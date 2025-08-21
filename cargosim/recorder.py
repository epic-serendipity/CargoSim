"""Recording functionality for CargoSim."""

import os
import time
import threading
import shutil
from types import SimpleNamespace
from typing import Literal, Optional

from .utils import ensure_mp4_ext, tmp_mp4_path, _mp4_available


class Recorder:
    def __init__(
        self,
        *,
        mode: Literal["live", "offline"],
        folder: Optional[str] = None,
        file_path: Optional[str] = None,
        fps: int,
        fmt: str,
        async_writer: bool = False,
        max_queue: int = 64,
        drop_on_backpressure: bool = True,
    ):
        fmt = fmt.lower().strip()
        if fmt not in ("mp4", "png"):
            raise ValueError("fmt must be 'mp4' or 'png'")

        self.mode = mode
        self.live = (mode == "live")
        self.fps = fps
        self.fmt = fmt
        self.frame_idx = 0
        self.frames_dropped = 0
        self.queue: Optional["queue.Queue"] = None
        self.thread: Optional[threading.Thread] = None
        self.writer = None
        self.out_path: Optional[str] = None
        self.tmp_path: Optional[str] = None
        self.final_path: Optional[str] = None
        self.drop_on_backpressure = drop_on_backpressure

        if self.live:
            if not folder:
                self.live = False
                return
            os.makedirs(folder, exist_ok=True)
            ts = time.strftime("%Y%m%d_%H%M%S")
            if fmt == "mp4":
                ok, why = _mp4_available()
                if not ok:
                    raise RuntimeError(
                        "MP4 recording requires imageio-ffmpeg; install extras: video, or switch to PNG frames."
                        + (f" Details: {why}" if why else "")
                    )
                self.out_path = os.path.join(folder, f"session_{ts}.mp4")
                if async_writer:
                    import queue
                    self.queue = queue.Queue(maxsize=max_queue)
                    self.thread = threading.Thread(target=self._worker_mp4, daemon=True)
                    self.thread.start()
                else:
                    import imageio.v2 as imageio
                    self.writer = imageio.get_writer(
                        self.out_path,
                        format="FFMPEG",
                        fps=fps,
                        codec="libx264",
                        quality=8,
                        macro_block_size=None,
                    )
            else:
                self.frame_dir = os.path.join(folder, "frames", f"session_{ts}")
                os.makedirs(self.frame_dir, exist_ok=True)
                self.out_path = self.frame_dir
                if async_writer:
                    import queue
                    self.queue = queue.Queue(maxsize=max_queue)
                    self.thread = threading.Thread(target=self._worker_png, daemon=True)
                    self.thread.start()
        else:
            if not file_path:
                raise ValueError("file_path required for offline recorder")
            self.out_path = file_path

    @classmethod
    def for_live(
        cls,
        folder: str,
        fps: int,
        fmt: str,
        async_writer: bool,
        max_queue: int,
        drop_on_backpressure: bool,
    ) -> "Recorder":
        fmt = fmt.lower().strip()
        return cls(
            mode="live",
            folder=folder,
            fps=fps,
            fmt=fmt,
            async_writer=async_writer,
            max_queue=max_queue,
            drop_on_backpressure=drop_on_backpressure,
        )

    @classmethod
    def for_offline(cls, file_path: str, fps: int, fmt: str) -> "Recorder":
        fmt = fmt.lower().strip()
        rec = cls(mode="offline", file_path=file_path, fps=fps, fmt=fmt)
        file_path = ensure_mp4_ext(os.path.abspath(file_path)) if fmt == "mp4" else os.path.abspath(file_path)
        if fmt == "mp4":
            ok, why = _mp4_available()
            if not ok:
                raise RuntimeError(
                    "MP4 rendering requires imageio-ffmpeg; install extras: video, or switch to PNG frames."
                    + (f" Details: {why}" if why else "")
                )
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            tmp_path = tmp_mp4_path(file_path)
            rec.out_path = file_path
            rec.tmp_path = tmp_path
            rec.final_path = file_path
            import imageio.v2 as imageio
            rec.writer = imageio.get_writer(
                tmp_path,
                format="FFMPEG",
                fps=fps,
                codec="libx264",
                quality=8,
                macro_block_size=None,
                pixelformat="yuv420p",
            )
        elif fmt == "png":
            stem, _ = os.path.splitext(file_path)
            rec.frame_dir_tmp = stem + "_frames.part"
            rec.frame_dir = stem + "_frames"
            os.makedirs(rec.frame_dir_tmp, exist_ok=True)
            rec.out_path = file_path
        else:
            raise ValueError(f"Unknown offline format: {fmt}")
        return rec

    def _enqueue(self, arr):
        if not self.queue:
            self._write_frame(arr)
            return
        try:
            self.queue.put_nowait(arr)
        except Exception:
            if self.drop_on_backpressure:
                self.frames_dropped += 1
            else:
                try:
                    self.queue.put(arr, timeout=0.005)
                except Exception:
                    self.frames_dropped += 1

    def capture(self, surface):
        if not self.live and self.mode != "offline":
            return
        if self.fmt == "png" and not self.live:
            path = os.path.join(self.frame_dir_tmp, f"frame_{self.frame_idx:06d}.png")
            # Lazy import of pygame only when needed
            try:
                import pygame
                pygame.image.save(surface, path)
            except ImportError:
                raise RuntimeError("pygame is required for PNG recording")
            self.frame_idx += 1
            return
        # Lazy import of pygame only when needed
        try:
            import pygame
            surf = surface
            arr = pygame.surfarray.array3d(surf).swapaxes(0, 1)
        except ImportError:
            raise RuntimeError("pygame is required for recording")
        if self.live:
            self._enqueue(arr)
        else:
            self._write_frame(arr)
        self.frame_idx += 1

    def _write_frame(self, arr):
        if self.fmt == "mp4":
            if not self.writer:
                return
            self.writer.append_data(arr)
        else:
            import imageio
            path = os.path.join(self.frame_dir, f"frame_{self.frame_idx:06d}.png")
            imageio.imwrite(path, arr)

    def _worker_mp4(self):
        import queue
        import imageio.v2 as imageio
        writer = imageio.get_writer(
            self.out_path,
            format="FFMPEG",
            fps=self.fps,
            codec="libx264",
            quality=8,
            macro_block_size=None,
        )
        while True:
            try:
                arr = self.queue.get()
            except queue.Empty:
                continue
            if arr is None:
                break
            writer.append_data(arr)
        writer.close()

    def _worker_png(self):
        import queue, imageio
        idx = 0
        while True:
            try:
                arr = self.queue.get()
            except queue.Empty:
                continue
            if arr is None:
                break
            path = os.path.join(self.frame_dir, f"frame_{idx:06d}.png")
            imageio.imwrite(path, arr)
            idx += 1

    def close(self, success: bool = True):
        if self.live:
            if self.queue and self.thread:
                self.queue.put(None)
                self.thread.join(timeout=5)
            elif self.writer:
                self.writer.close()
            return self.out_path
        else:
            if self.fmt == "mp4":
                if self.writer:
                    self.writer.close()
                if success:
                    if self.tmp_path and self.final_path:
                        os.replace(self.tmp_path, self.final_path)
                else:
                    if self.tmp_path and os.path.exists(self.tmp_path):
                        os.remove(self.tmp_path)
            elif self.fmt == "png":
                if success:
                    os.replace(self.frame_dir_tmp, self.frame_dir)
                    self.out_path = self.frame_dir
                else:
                    if os.path.isdir(self.frame_dir_tmp):
                        shutil.rmtree(self.frame_dir_tmp, ignore_errors=True)
            return (self.final_path if self.fmt == "mp4" else self.out_path) if success else None

    def finalize(self):
        return self.close()


class NullRecorder:
    """Null recorder that does nothing - used when recording is disabled."""
    live = False
    frames_dropped = 0
    frame_idx = 0

    def capture(self, _surface):
        return
        
    def close(self, success: bool = True):
        return None

    def finalize(self):
        return self.close()
