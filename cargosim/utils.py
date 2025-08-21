"""Utility functions and constants for CargoSim."""

import os
import logging
import sys
import traceback
from typing import List, Optional
from datetime import datetime

# Debug logging
DEBUG_LOG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cargo_sim_debug.log")
# Runtime logging for execution tracking
RUNTIME_LOG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cargo_sim_runtime.log")

# Setup logging
def setup_logging(level: str = "INFO", log_file: Optional[str] = None, 
                  console: bool = True) -> logging.Logger:
    """Setup logging configuration for CargoSim."""
    logger = logging.getLogger("cargosim")
    logger.setLevel(getattr(logging, level.upper()))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Console handler
    if console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def setup_runtime_logging() -> logging.Logger:
    """Setup specialized runtime logging for execution tracking."""
    runtime_logger = logging.getLogger("cargosim.runtime")
    runtime_logger.setLevel(logging.DEBUG)
    
    # Clear existing handlers
    runtime_logger.handlers.clear()
    
    # Create detailed formatter for runtime
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    )
    
    # File handler for runtime log
    file_handler = logging.FileHandler(RUNTIME_LOG, encoding="utf-8", mode="w")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    runtime_logger.addHandler(file_handler)
    
    # Console handler for runtime (INFO level only)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    runtime_logger.addHandler(console_handler)
    
    return runtime_logger


def log_runtime_event(event: str, details: str = "", level: str = "INFO"):
    """Log a runtime event with timestamp and details."""
    runtime_logger = logging.getLogger("cargosim.runtime")
    
    # Add execution context
    import inspect
    frame = inspect.currentframe().f_back
    if frame:
        filename = os.path.basename(frame.f_code.co_filename)
        lineno = frame.f_lineno
        func_name = frame.f_code.co_name
        context = f"{filename}:{lineno}:{func_name}"
    else:
        context = "unknown"
    
    message = f"[{context}] {event}"
    if details:
        message += f" - {details}"
    
    if level.upper() == "DEBUG":
        runtime_logger.debug(message)
    elif level.upper() == "INFO":
        runtime_logger.info(message)
    elif level.upper() == "WARNING":
        runtime_logger.warning(message)
    elif level.upper() == "ERROR":
        runtime_logger.error(message)
    elif level.upper() == "CRITICAL":
        runtime_logger.critical(message)


def log_exception(e: Exception, context: str = ""):
    """Log an exception with full traceback."""
    runtime_logger = logging.getLogger("cargosim.runtime")
    
    message = f"EXCEPTION in {context}: {type(e).__name__}: {str(e)}"
    runtime_logger.error(message)
    
    # Log full traceback
    traceback_str = traceback.format_exc()
    runtime_logger.error(f"Traceback:\n{traceback_str}")


def get_logger(name: str = "cargosim") -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)


def append_debug(lines: List[str]):
    """Append debug lines to the debug log file (legacy function)."""
    try:
        with open(DEBUG_LOG, "a", encoding="utf-8") as f:
            for ln in lines:
                f.write(ln + "\n")
    except Exception:
        pass


def clamp(val, lo, hi):
    """Clamp a value between low and high bounds."""
    return max(lo, min(hi, val))


def ellipsize(text: str, font, max_w: int) -> str:
    """Truncate text with ellipsis so rendered width ≤ max_w."""
    if font.size(text)[0] <= max_w - 2:
        return text
    out = text
    while out and font.size(out + "...")[0] > max_w:
        out = out[:-1]
    return out + "..." if out else "..."


def ensure_mp4_ext(path: str) -> str:
    """Ensure path has .mp4 extension."""
    if not path.lower().endswith('.mp4'):
        path += '.mp4'
    return path


def tmp_mp4_path() -> str:
    """Get temporary MP4 path."""
    import tempfile
    return os.path.join(tempfile.gettempdir(), f"cargo_sim_{os.getpid()}.mp4")


def _mp4_available() -> tuple[bool, str]:
    """Check if MP4 recording is available."""
    try:
        import imageio
        import imageio_ffmpeg
        return True, "imageio-ffmpeg available"
    except ImportError:
        return False, "imageio-ffmpeg not available"
