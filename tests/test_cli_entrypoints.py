import sys
import os
import sys
from types import SimpleNamespace

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import cargo_sim
import cargosim.__main__ as cm


def test_python_m_cargosim(monkeypatch):
    called = SimpleNamespace(count=0)

    def fake_main():
        called.count += 1
    monkeypatch.setattr(cargo_sim, "main", fake_main)
    monkeypatch.setattr(cm, "gui_main", fake_main)
    cm.main([])
    assert called.count == 1


def test_headless_exits_zero():
    assert cm.headless(["--periods", "4", "--seed", "1"]) == 0
