import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import pygame

from cargo_sim import LogisticsSim, SimConfig, Renderer


def test_fullscreen_default():
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    cfg = SimConfig()
    sim = LogisticsSim(cfg)
    rnd = Renderer(sim)
    assert rnd.fullscreen
    assert rnd.screen.get_flags() & pygame.FULLSCREEN
    pygame.quit()
