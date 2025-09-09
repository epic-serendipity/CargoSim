import ast
import sys
from pathlib import Path

import pytest


def project_root() -> Path:
    # Resolve to repository root by walking up from this test file
    p = Path(__file__).resolve()
    for parent in p.parents:
        # Heuristic: repo contains the top-level package directory
        if (parent / "cargosim").is_dir() and (parent / "pytest.ini").exists():
            return parent
    # Fallback: two levels up from tests/unit/... structure
    return Path(__file__).resolve().parents[3]


def iter_python_files(root: Path):
    """Yield all .py files in the repo excluding tests and typical build/venv dirs."""
    exclude_dirs = {
        ".git",
        "__pycache__",
        "build",
        "dist",
        "venv",
        ".venv",
        "env",
        ".tox",
        "site-packages",
        "tests",
        "docs",
    }

    for path in root.rglob("*.py"):
        # Skip excluded directories anywhere in the path
        if any(part in exclude_dirs for part in path.parts):
            continue
        yield path


def iter_python_files_for_imports(root: Path):
    """Yield all .py files that can act as importers (include tests), but skip env/build."""
    exclude_dirs = {
        ".git",
        "__pycache__",
        "build",
        "dist",
        "venv",
        ".venv",
        "env",
        ".tox",
        "site-packages",
        "docs",
    }

    for path in root.rglob("*.py"):
        if any(part in exclude_dirs for part in path.parts):
            continue
        yield path


def module_name_for_file(pkg_root: Path, file_path: Path) -> str | None:
    try:
        rel = file_path.relative_to(pkg_root)
    except ValueError:
        return None
    if rel.suffix != ".py":
        return None
    parts = list(rel.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    name = ".".join([pkg_root.name] + parts) if parts else pkg_root.name
    return name


def resolve_relative(base_module: str, level: int, module: str | None) -> str | None:
    # Resolve 'from .x import y' to absolute module
    base_parts = base_module.split(".")
    if level > len(base_parts):
        return None
    prefix = base_parts[: len(base_parts) - level]
    if module:
        return ".".join(prefix + module.split(".")) if prefix else module
    return ".".join(prefix) if prefix else None


def read_text_safely(p: Path) -> str | None:
    """Read a file as text, handling UTF-8 BOM if present."""
    try:
        return p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            return p.read_text(encoding="utf-8-sig")
        except Exception:
            return None
    except Exception:
        return None


def _is_notimplemented_raise(node: ast.stmt) -> bool:
    if isinstance(node, ast.Raise) and node.exc is not None:
        # raise NotImplementedError or raise NotImplementedError()
        exc = node.exc
        # Name
        if isinstance(exc, ast.Name) and exc.id == "NotImplementedError":
            return True
        # Call
        if isinstance(exc, ast.Call):
            func = exc.func
            if isinstance(func, ast.Name) and func.id == "NotImplementedError":
                return True
            if isinstance(func, ast.Attribute) and func.attr == "NotImplementedError":
                return True
        # Attribute, e.g., exceptions.NotImplementedError
        if isinstance(exc, ast.Attribute) and exc.attr == "NotImplementedError":
            return True
    return False


def _strip_docstring(body):
    if not body:
        return body
    first = body[0]
    # Remove a leading docstring expression
    if isinstance(first, ast.Expr) and isinstance(getattr(first, "value", None), ast.Constant) and isinstance(first.value.value, str):
        return body[1:]
    return body


@pytest.mark.unit
def test_no_unimplemented_stubs_in_repo():
    """
    Fail if any function/method exists whose body is only a NotImplementedError
    raise or an ellipsis expression. This surfaces intentionally unimplemented
    functions left in the codebase.
    """
    root = project_root()
    offenders = []

    for pyfile in iter_python_files(root):
        source = read_text_safely(pyfile)
        if source is None:
            # Skip unreadable files
            continue
        try:
            tree = ast.parse(source, filename=str(pyfile))
        except SyntaxError:
            # Retry parsing after stripping potential BOM
            try:
                tree = ast.parse(source.lstrip("\ufeff"), filename=str(pyfile))
            except SyntaxError:
                # Ignore non-parseable files
                continue

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                body = _strip_docstring(node.body)
                if not body:
                    continue
                # Single statement bodies that indicate an unimplemented stub
                if len(body) == 1:
                    only = body[0]
                    # raise NotImplementedError
                    if _is_notimplemented_raise(only):
                        offenders.append((pyfile, node.lineno, node.name, "raises NotImplementedError"))
                        continue
                    # body is just an ellipsis expression: ...
                    if isinstance(only, ast.Expr) and isinstance(getattr(only, "value", None), ast.Constant) and only.value.value is Ellipsis:
                        offenders.append((pyfile, node.lineno, node.name, "uses ellipsis (...) stub"))
                        continue

    if offenders:
        lines = [
            f"Unimplemented function stubs found ({len(offenders)}):",
        ]
        for f, lineno, name, reason in offenders[:25]:
            lines.append(f" - {f}:{lineno} -> {name} ({reason})")
        if len(offenders) > 25:
            lines.append(f" ... and {len(offenders) - 25} more")
        pytest.fail("\n".join(lines))


@pytest.mark.unit
def test_dead_code_with_vulture_if_available():
    """
    If the 'vulture' package is installed, run it programmatically against the
    project package to detect obviously unused (dead) code. Skips if vulture is
    not available to keep the suite optional.
    """
    try:
        from vulture import Vulture  # type: ignore
    except Exception:
        pytest.skip("vulture not installed; skipping dead code scan")

    root = project_root()
    pkg = root / "cargosim"
    if not pkg.exists():
        pytest.skip("package directory not found; skipping dead code scan")

    # Configure vulture with conservative settings to reduce false positives.
    # Older vulture may not support 'min_confidence' in __init__.
    min_conf = 80
    try:
        v = Vulture(min_confidence=min_conf)
    except TypeError:
        v = Vulture()

    # Exclude tests and common non-source directories
    paths = [str(pkg)]
    try:
        v.scavenge(paths)  # type: ignore[attr-defined]
    except Exception:
        # Older versions used 'scan' instead of 'scavenge'
        scan = getattr(v, "scan", None)
        if callable(scan):
            scan(paths)
        else:
            pytest.skip("vulture API not supported in this environment")

    try:
        items = list(v.get_unused_code())  # type: ignore[attr-defined]
    except Exception:
        # Older versions used 'get_unused_items'
        getter = getattr(v, "get_unused_items", None)
        items = list(getter()) if callable(getter) else []

    # Apply confidence filter if available
    filtered = []
    for it in items:
        conf = getattr(it, "confidence", None)
        if conf is None or conf >= min_conf:
            filtered.append(it)

    if filtered:
        lines = [
            f"Potential dead code detected by vulture ({len(filtered)}) with confidence>={min_conf}:",
        ]
        shown = 0
        for it in filtered:
            # Fallback attribute access for different vulture versions
            filename = getattr(it, "filename", None) or getattr(it, "file", None) or "<unknown>"
            lineno = getattr(it, "lineno", None) or getattr(it, "line", None) or 0
            name = getattr(it, "name", None) or getattr(it, "message", None) or getattr(it, "typ", None) or "item"
            conf = getattr(it, "confidence", None)
            detail = f" - {filename}:{lineno} -> {name}"
            if conf is not None:
                detail += f" (confidence {conf})"
            lines.append(detail)
            shown += 1
            if shown >= 25:
                break
        if len(filtered) > shown:
            lines.append(f" ... and {len(filtered) - shown} more")
        pytest.fail("\n".join(lines))


@pytest.mark.unit
def test_no_unimported_modules_in_package():
    """
    Identify modules in the main package that are never imported anywhere in the
    project (including tests/scripts). Allows an opt-out via a file-level pragma:
    add `# pragma: allow-unused-module` at the top of a module to ignore it.
    """
    root = project_root()
    pkg = root / "cargosim"
    if not pkg.exists():
        pytest.skip("package directory not found; skipping module import scan")

    # Map module name -> file path and back
    name_for_path: dict[Path, str] = {}
    path_for_name: dict[str, Path] = {}

    for py in pkg.rglob("*.py"):
        if "__pycache__" in py.parts:
            continue
        mod = module_name_for_file(pkg, py)
        if not mod:
            continue
        name_for_path[py] = mod
        path_for_name[mod] = py

    # Collect imported module names across the repository
    used: set[str] = set()

    for src in iter_python_files_for_imports(root):
        text = read_text_safely(src)
        if text is None:
            continue
        try:
            tree = ast.parse(text, filename=str(src))
        except SyntaxError:
            try:
                tree = ast.parse(text.lstrip("\ufeff"), filename=str(src))
            except SyntaxError:
                continue

        # Determine the importer module name for relative resolution
        importer_mod: str | None = None
        if str(src).startswith(str(pkg)):
            importer_mod = module_name_for_file(pkg, src)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name
                    # Record exact name (e.g., cargosim.rendering.renderer)
                    used.add(name)
            elif isinstance(node, ast.ImportFrom):
                base = node.module
                # Resolve relative imports inside the package
                if node.level and importer_mod:
                    abs_base = resolve_relative(importer_mod, node.level, base)
                else:
                    abs_base = base
                if abs_base:
                    used.add(abs_base)
                # Attempt to resolve submodules imported via 'from pkg import sub'
                for alias in node.names:
                    if alias.name == "*":
                        continue
                    if abs_base:
                        candidate = f"{abs_base}.{alias.name}"
                        if candidate in path_for_name:
                            used.add(candidate)

    # Also consider parent packages used when a submodule is imported
    expanded_used: set[str] = set()
    for name in used:
        parts = name.split(".")
        for i in range(1, len(parts) + 1):
            expanded_used.add(".".join(parts[:i]))

    offenders = []
    for path, mod in name_for_path.items():
        # Optional file-level pragma to opt out
        try:
            head = path.read_text(encoding="utf-8").splitlines()[:5]
        except Exception:
            head = []
        pragma_opt_out = any("pragma: allow-unused-module" in line for line in head)
        if pragma_opt_out:
            continue

        if mod not in expanded_used:
            offenders.append((mod, path))

    if offenders:
        lines = [
            f"Unimported modules found in package ({len(offenders)}):",
        ]
        for mod, path in offenders[:25]:
            lines.append(f" - {mod} ({path})")
        if len(offenders) > 25:
            lines.append(f" ... and {len(offenders) - 25} more")
        pytest.fail("\n".join(lines))
