"""Main entry points for CargoSim."""

import os
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox

from .config import SimConfig, load_config, save_config, validate_config
from .simulation import LogisticsSim
from .renderer import Renderer
from .gui import ControlGUI
from .utils import setup_logging, get_logger, setup_runtime_logging, log_runtime_event, log_exception


def _pip_install(pkgs: list[str]) -> bool:
    """Install packages using pip."""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade"] + pkgs)
        return True
    except Exception as e:
        messagebox.showerror("Install Failed", f"Failed to install: {' '.join(pkgs)}\n{e}")
        return False


def check_and_offer_installs(startup_root: tk.Tk):
    """Ask user to install missing dependencies."""
    logger = get_logger("main.dependencies")
    log_runtime_event("Starting dependency check and install process")
    
    # Required: pygame - only check availability, don't import yet
    pygame_available = False
    try:
        log_runtime_event("Checking pygame availability")
        import importlib.util
        pygame_spec = importlib.util.find_spec("pygame")
        pygame_available = pygame_spec is not None
        if pygame_available:
            logger.info("pygame is available")
            log_runtime_event("pygame is available")
        else:
            logger.warning("pygame is not available")
            log_runtime_event("pygame is not available")
    except Exception as e:
        pygame_available = False
        logger.warning("pygame availability check failed")
        log_runtime_event("pygame availability check failed", f"error={e}")

    if not pygame_available:
        log_runtime_event("pygame not available, prompting user for installation")
        startup_root.deiconify()
        if messagebox.askyesno("Dependency Required",
                               "Required dependency 'pygame' is not installed.\nInstall it now?"):
            logger.info("User chose to install pygame")
            log_runtime_event("User chose to install pygame")
            ok = _pip_install(["pygame"])
            if ok:
                try:
                    log_runtime_event("Verifying pygame installation")
                    import importlib
                    import pygame as _pg  # noqa
                    importlib.reload(sys.modules.get("pygame", _pg))
                    pygame_available = True
                    logger.info("pygame installed successfully")
                    log_runtime_event("pygame installed and verified successfully")
                except Exception as e:
                    pygame_available = True  # best effort
                    logger.warning("pygame installation verification failed")
                    log_runtime_event("pygame installation verification failed", f"error={e}")
                if messagebox.askyesno("Restart Needed", "Pygame installed. Restart the app now?"):
                    logger.info("Restarting application after pygame installation")
                    log_runtime_event("Restarting application after pygame installation")
                    os.execl(sys.executable, sys.executable, *sys.argv)
        else:
            logger.warning("User declined pygame installation")
            log_runtime_event("User declined pygame installation")
            messagebox.showwarning("Simulation Disabled", "Without pygame, the simulation and offline render are disabled.")
    
    if pygame_available:
        log_runtime_event("pygame available, enabling simulation features")
        if hasattr(startup_root, 'start_btn'):
            startup_root.start_btn.state(["!disabled"])
        if hasattr(startup_root, 'offline_btn'):
            startup_root.offline_btn.state(["!disabled"])
    
    # Optional: imageio & imageio-ffmpeg
    log_runtime_event("Checking MP4 recording dependencies")
    from .utils import _mp4_available
    if not _mp4_available()[0]:
        logger.warning("MP4 recording not available")
        log_runtime_event("MP4 recording not available")
        if messagebox.askyesno("Optional Feature: MP4",
                               "Optional dependency 'imageio-ffmpeg' not installed.\n"
                               "Install to enable MP4 assembly for recordings?\n"
                               "You can still export PNG frames without it."):
            logger.info("User chose to install MP4 dependencies")
            log_runtime_event("User chose to install MP4 dependencies")
            ok = _pip_install(["imageio", "imageio-ffmpeg"])
            if ok:
                try:
                    log_runtime_event("Verifying MP4 dependencies installation")
                    import importlib
                    import imageio.v2 as _io
                    import imageio
                    imageio = _io
                    logger.info("MP4 dependencies installed successfully")
                    log_runtime_event("MP4 dependencies installed and verified successfully")
                except Exception as e:
                    logger.warning(f"MP4 dependencies installation verification failed: {e}")
                    log_runtime_event("MP4 dependencies installation verification failed", f"error={e}")
    
    log_runtime_event("Dependency check and install process completed")


def run_sim(cfg: SimConfig, *, force_windowed: bool = False):
    """Run the simulation with the given configuration."""
    logger = get_logger("main.simulation")
    log_runtime_event("Starting run_sim function", f"fleet={cfg.fleet_label}, periods={cfg.periods}, force_windowed={force_windowed}")
    
    # Validate configuration before running
    log_runtime_event("Validating simulation configuration")
    validation_issues = validate_config(cfg)
    if validation_issues:
        logger.warning(f"Configuration validation issues: {validation_issues}")
        log_runtime_event("Configuration validation issues found", f"issues={validation_issues}")
        messagebox.showwarning("Configuration Issues", 
                              "Configuration has some issues:\n" + "\n".join(validation_issues))
    else:
        log_runtime_event("Configuration validation passed")
    
    logger.info(f"Starting simulation with fleet: {cfg.fleet_label}, periods: {cfg.periods}")
    
    # Initialize simulation and renderer variables
    sim = None
    renderer = None
    
    try:
        log_runtime_event("Creating LogisticsSim instance")
        sim = LogisticsSim(cfg)
        log_runtime_event("LogisticsSim created successfully")
        
        log_runtime_event("Creating Renderer instance", f"force_windowed={force_windowed}")
        renderer = Renderer(sim, force_windowed=force_windowed)
        log_runtime_event("Renderer created successfully")
        
        log_runtime_event("Starting renderer.run()")
        live_out = renderer.run()
        log_runtime_event("Renderer.run() completed successfully", f"live_out={live_out}")
        
        # If simulation completed, keep the pygame window open
        if renderer.exit_code == "COMPLETE":
            log_runtime_event("Simulation completed - keeping pygame window open")
            logger.info("Simulation completed - pygame window will remain open. Press ESC to return to control panel.")
            
            # Keep the window open until user closes it
            keep_window_open(renderer)
        else:
            log_runtime_event("Simulation ended normally - closing pygame window")
        
        log_runtime_event("Updating configuration with renderer settings")
        cfg.launch_fullscreen = renderer.fullscreen
        save_config(cfg)
        
        logger.info("Simulation completed successfully")
        log_runtime_event("Simulation completed successfully", f"exit_code={renderer.exit_code}")
        return renderer.exit_code, live_out
        
    except Exception as e:
        log_exception(e, "run_sim function")
        logger.error(f"Simulation failed: {e}")
        messagebox.showerror("Simulation Error", f"Simulation failed: {e}")
        raise
    finally:
        # Ensure proper cleanup regardless of how the simulation ends
        log_runtime_event("Ensuring simulation cleanup in finally block")
        try:
            if renderer and renderer.exit_code == "GUI":
                log_runtime_event("Simulation returning to GUI - performing final cleanup")
                # Additional cleanup for GUI return
                if hasattr(renderer, '_cleanup_simulation'):
                    renderer._cleanup_simulation()
                
                # Use the renderer's quit_pygame method for proper cleanup
                if hasattr(renderer, 'quit_pygame'):
                    renderer.quit_pygame()
                else:
                    # Fallback cleanup if the method doesn't exist
                    try:
                        import pygame
                        pygame.display.quit()
                        log_runtime_event("pygame display quit successfully (fallback)")
                    except Exception as e:
                        log_runtime_event("Error quitting pygame display (fallback)", f"error={e}")
                    
                    # Clear any remaining pygame surfaces
                    try:
                        if hasattr(renderer, 'screen'):
                            renderer.screen = None
                        if hasattr(renderer, 'surface'):
                            renderer.surface = None
                        log_runtime_event("Pygame surfaces cleared (fallback)")
                    except Exception as e:
                        log_runtime_event("Error clearing pygame surfaces (fallback)", f"error={e}")
            
            # Clear simulation object references
            if sim:
                try:
                    # Clear any remaining simulation data
                    if hasattr(sim, 'actions_log'):
                        sim.actions_log.clear()
                    if hasattr(sim, 'history'):
                        sim.history.clear()
                    if hasattr(sim, 'stock'):
                        sim.stock.clear()
                    if hasattr(sim, 'fleet'):
                        sim.fleet.clear()
                    log_runtime_event("Simulation object references cleared")
                except Exception as e:
                    log_runtime_event("Error clearing simulation object references", f"error={e}")
                
                sim = None
            
            if renderer:
                renderer = None
                
            log_runtime_event("Final cleanup completed")
            
        except Exception as e:
            log_runtime_event("Error during final cleanup", f"error={e}")
            # Don't raise cleanup errors


def keep_window_open(renderer):
    """Keep the pygame window open after simulation completion until user closes it."""
    try:
        log_runtime_event("Starting keep_window_open function")
        
        # Create a simple event loop to keep the window responsive
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    log_runtime_event("User closed pygame window")
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                        log_runtime_event("User pressed ESC to return to control panel")
                    elif event.key == pygame.K_F11:
                        renderer._toggle_fullscreen()
                        log_runtime_event("User toggled fullscreen")
                    elif event.key == pygame.K_d:
                        renderer.show_debug = not renderer.show_debug
                        log_runtime_event("User toggled debug overlay")
            
            # Render the completion state
            renderer.render_frame([], 1.0)
            pygame.display.flip()
            
            # Cap frame rate
            renderer.clock.tick(30)
        
        log_runtime_event("keep_window_open loop completed")
        
    except Exception as e:
        log_exception(e, "keep_window_open function")
        logger.error(f"Error in keep_window_open: {e}")
    finally:
        # Clean up pygame when the window is finally closed
        try:
            pygame.quit()
            log_runtime_event("pygame.quit() called after window close")
        except:
            pass


def render_offline(cfg: SimConfig):
    """Render a video directly from current config without interactive playback."""
    # Only import pygame when actually needed for offline rendering
    try:
        import pygame
    except ImportError:
        raise RuntimeError("pygame is required for offline rendering.")

    # headless surface rendering
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    import pygame as pg
    pg.init()
    rc = cfg.recording
    cfg.right_panel_view = rc.record_right_panel_view
    if rc.record_resolution_mode == "display":
        if rc.last_fullscreen_size:
            w, h = rc.last_fullscreen_size
        else:
            w, h = (1920, 1080)
    else:
        w, h = rc.record_custom_width, rc.record_custom_height

    # Build sim and a faux renderer that draws onto our surface without display
    class Headless(Renderer):
        def __init__(self, sim, width, height):
            # Call parent constructor but don't initialize pygame yet
            super().__init__(sim, force_windowed=True)
            
            # Override attributes for headless mode
            self.fullscreen = False
            self.flags = 0
            self.mode = "offline"
            
            # Initialize headless display
            self._init_display_headless_safe()
            self._apply_theme()
            try:
                self._init_gfx_pipeline(width, height)
            except ValueError:
                self._init_gfx_pipeline(1920, 1080)
            self.surface = pygame.Surface((width, height), flags=pygame.SRCALPHA)
            self.screen = self.surface
            self.clock = None

            # Initialize remaining attributes
            from .config import CURSOR_COLORS, hex2rgb
            self.cursor_col = hex2rgb(CURSOR_COLORS.get(self.sim.cfg.cursor_color, CURSOR_COLORS["Cobalt"]))
            self.ac_colors = {k: hex2rgb(v) for k, v in self.sim.cfg.theme.ac_colors.items()}
            self.bar_cols = [self.tt.bar_A, self.tt.bar_B, self.tt.bar_C, self.tt.bar_D]

            self.period_seconds = float(self.sim.cfg.period_seconds)
            self.paused = False
            from types import SimpleNamespace
            self.recorder = SimpleNamespace(live=True, frames_dropped=0, frame_idx=0)
            self._last_heading_by_ac = {}

        def run(self):
            pass

    sim = LogisticsSim(cfg)
    rnd = Headless(sim, w, h)
    rnd.include_side_panels = getattr(cfg, "viz_include_side_panels", True)
    rnd.right_panel_mode = getattr(
        cfg, "viz_right_panel_mode", getattr(cfg, "right_panel_view", "ops_total_sparkline")
    )
    rnd.show_stats_overlay = getattr(cfg, "viz_show_stats_overlay", False)

    frames_per_period = max(1, rc.frames_per_period)

    fmt = rc.offline_fmt
    from .utils import _mp4_available
    ok, _ = _mp4_available()
    if fmt == "mp4" and not ok:
        logger.warning("MP4 rendering requires imageio-ffmpeg; writing PNG frames instead.")
        fmt = "png"
    ext = ".mp4" if fmt == "mp4" else ".png"
    out_file = rc.offline_output_path or os.path.join(os.getcwd(), f"offline_render{ext}")
    from .recorder import Recorder
    recorder = Recorder.for_offline(file_path=out_file, fps=rc.offline_fps, fmt=fmt)

    try:
        for period in range(cfg.periods):
            actions = sim.actions_log[-1] if sim.actions_log else []
            for f in range(frames_per_period):
                alpha = (f + 1) / frames_per_period
                rnd.recorder.frame_idx = recorder.frame_idx
                rnd.render_frame(actions, alpha, with_overlays=True)
                recorder.capture(rnd.surface)
            sim.step_period()
        out_path = recorder.close()
        pg.quit()
        return out_path
    except Exception:
        recorder.close(success=False)
        pg.quit()
        raise


def theme_sweep(out_dir: str = "_theme_sweep"):
    """Generate theme preview images."""
    os.makedirs(out_dir, exist_ok=True)
    from .config import THEME_PRESETS, AIRFRAME_COLORSETS
    for name in THEME_PRESETS.keys():
        cfg = SimConfig()
        from .config import apply_theme_preset
        apply_theme_preset(cfg.theme, name)
        if cfg.theme.ac_colorset:
            cfg.theme.ac_colors = AIRFRAME_COLORSETS[cfg.theme.ac_colorset]
        cfg.periods = 2
        cfg.recording.frames_per_period = 1
        cfg.recording.record_live_format = "png"
        cfg.recording.offline_fmt = "png"
        slug = name.replace(" ", "_")
        cfg.recording.offline_output_path = os.path.join(out_dir, f"{slug}.png")
        render_offline(cfg)

        def luminance(rgb):
            def chan(c):
                c /= 255
                return c/12.92 if c <= 0.03928 else ((c+0.055)/1.055) ** 2.4
            r,g,b = [chan(x) for x in rgb]
            return 0.2126*r + 0.7152*g + 0.0722*b
        from .config import hex2rgb
        fg = hex2rgb(cfg.theme.game_fg); bg = hex2rgb(cfg.theme.game_bg)
        L1, L2 = luminance(fg), luminance(bg)
        ratio = (max(L1,L2)+0.05)/(min(L1,L2)+0.05)
        if ratio < 4.5:
            logger.warning(f"Contrast warning for {name}: {ratio:.2f}")
        bars = [hex2rgb(cfg.theme.bar_A), hex2rgb(cfg.theme.bar_B), hex2rgb(cfg.theme.bar_C), hex2rgb(cfg.theme.bar_D)]
        for i in range(4):
            for j in range(i+1,4):
                diff = sum(abs(bars[i][k]-bars[j][k]) for k in range(3))
                if diff < 40:
                    logger.warning(f"Bar color similarity warning in {name}: {i} vs {j}")
    logger.info(f"Theme sweep output written to {out_dir}")


def main(*, force_windowed: bool = False):
    """Main entry point for the GUI."""
    try:
        # Setup runtime logging at the start of main()
        runtime_logger = setup_runtime_logging()
        log_runtime_event("Starting CargoSim main function", f"force_windowed={force_windowed}")
        
        # dependencies prompt on startup
        log_runtime_event("Creating temporary Tkinter root for dependency check")
        tmp = tk.Tk()
        tmp.withdraw()
        
        log_runtime_event("Checking and offering dependency installations")
        check_and_offer_installs(tmp)
        
        log_runtime_event("Destroying temporary root")
        tmp.destroy()

        log_runtime_event("Loading configuration")
        cfg = load_config()
        log_runtime_event("Configuration loaded successfully", f"config_version={cfg.config_version}")

        log_runtime_event("Creating main Tkinter root window")
        root = tk.Tk()
        log_runtime_event("Main root window created")
        
        # Apply the comprehensive theme system early in startup
        log_runtime_event("Importing UI theme modules")
        from .ui_theme import apply_theme, create_palette_from_theme_config
        
        log_runtime_event("Creating theme palette from configuration")
        palette = create_palette_from_theme_config(cfg.theme)
        log_runtime_event("Theme palette created", f"palette_keys={list(palette.keys())}")
        
        log_runtime_event("Applying comprehensive theme to root window")
        apply_theme(root, palette)
        log_runtime_event("Theme applied successfully")
        
        log_runtime_event("Creating ControlGUI instance")
        ControlGUI(root, cfg, force_windowed=force_windowed)
        log_runtime_event("ControlGUI created successfully")
        
        log_runtime_event("Starting Tkinter mainloop")
        root.mainloop()
        log_runtime_event("Tkinter mainloop completed")
        
    except Exception as e:
        log_exception(e, "main function")
        # Re-raise to ensure the error is visible
        raise


if __name__ == "__main__":
    try:
        # Setup runtime logging at startup
        runtime_logger = setup_runtime_logging()
        log_runtime_event("CargoSim startup initiated", f"argv={sys.argv}")
        
        if "--offline-render" in sys.argv:
            log_runtime_event("Offline render mode detected")
            cfg = load_config()
            out = render_offline(cfg)
            log_runtime_event("Offline render completed", f"output={out}")
            logger.info(out)
        elif "--theme-sweep" in sys.argv:
            log_runtime_event("Theme sweep mode detected")
            theme_sweep()
            log_runtime_event("Theme sweep completed")
        else:
            log_runtime_event("GUI mode detected", f"force_windowed={'--windowed' in sys.argv}")
            main(force_windowed="--windowed" in sys.argv)
            
    except Exception as e:
        log_exception(e, "main entry point")
        # Print to stderr to ensure error is visible
        print(f"FATAL ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
