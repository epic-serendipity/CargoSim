import os
import sys

import pytest

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import pygame

from cargosim import LogisticsSim, SimConfig, Renderer

pytest.skip("Fullscreen rendering not available in test environment", allow_module_level=True)


def test_fullscreen_default():
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    cfg = SimConfig()
    sim = LogisticsSim(cfg)
    rnd = Renderer(sim)
    assert rnd.fullscreen
    assert rnd.screen.get_flags() & pygame.FULLSCREEN
    pygame.quit()
