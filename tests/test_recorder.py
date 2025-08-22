"""Tests for the recording system."""

import pytest
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock, mock_open
import threading
import time

from cargosim.recorder import Recorder, NullRecorder


class TestNullRecorder:
    """Test NullRecorder functionality."""
    
    def test_null_recorder_creation(self):
        """Test NullRecorder initialization."""
        recorder = NullRecorder()
        
        assert recorder.live is False
        assert recorder.frames_dropped == 0
        assert recorder.frame_idx == 0
    
    def test_null_recorder_capture(self):
        """Test NullRecorder capture method."""
        recorder = NullRecorder()
        
        # Should not raise any exceptions
        recorder.capture(None)
        recorder.capture("fake_surface")
        
        # Frame count should remain zero
        assert recorder.frame_idx == 0
    
    def test_null_recorder_close(self):
        """Test NullRecorder close method."""
        recorder = NullRecorder()
        
        result = recorder.close()
        assert result is None
        
        result = recorder.close(success=False)
        assert result is None
    
    def test_null_recorder_finalize(self):
        """Test NullRecorder finalize method."""
        recorder = NullRecorder()
        
        result = recorder.finalize()
        assert result is None


class TestRecorderInitialization:
    """Test Recorder initialization."""
    
    def test_recorder_invalid_format(self):
        """Test recorder with invalid format."""
        with pytest.raises(ValueError, match="fmt must be 'mp4' or 'png'"):
            Recorder(
                mode="live",
                folder="/tmp",
                fps=30,
                fmt="avi"  # Invalid format
            )
    
    def test_recorder_live_mode_no_folder(self):
        """Test live recorder without folder."""
        recorder = Recorder(
            mode="live",
            folder=None,  # No folder provided
            fps=30,
            fmt="png"
        )
        
        # Should disable live mode
        assert recorder.live is False
    
    def test_recorder_offline_mode_no_file_path(self):
        """Test offline recorder without file path."""
        with pytest.raises(ValueError, match="file_path required for offline recorder"):
            Recorder(
                mode="offline",
                fps=30,
                fmt="mp4"
            )
    
    def test_recorder_basic_attributes(self):
        """Test basic recorder attributes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            recorder = Recorder(
                mode="live",
                folder=temp_dir,
                fps=30,
                fmt="png"
            )
            
            assert recorder.mode == "live"
            assert recorder.live is True
            assert recorder.fps == 30
            assert recorder.fmt == "png"
            assert recorder.frame_idx == 0
            assert recorder.frames_dropped == 0


class TestLivePNGRecording:
    """Test live PNG recording."""
    
    def test_live_png_sync_recording(self):
        """Test live PNG recording in synchronous mode."""
        with tempfile.TemporaryDirectory() as temp_dir:
            recorder = Recorder(
                mode="live",
                folder=temp_dir,
                fps=30,
                fmt="png",
                async_writer=False
            )
            
            assert recorder.live is True
            assert recorder.fmt == "png"
            assert recorder.queue is None
            assert recorder.thread is None
            assert os.path.exists(recorder.frame_dir)
    
    def test_live_png_async_recording(self):
        """Test live PNG recording in asynchronous mode."""
        with tempfile.TemporaryDirectory() as temp_dir:
            recorder = Recorder(
                mode="live",
                folder=temp_dir,
                fps=30,
                fmt="png",
                async_writer=True,
                max_queue=10
            )
            
            assert recorder.live is True
            assert recorder.queue is not None
            assert recorder.thread is not None
            assert recorder.thread.daemon is True
            
            # Clean up
            recorder.close()


class TestLiveMP4Recording:
    """Test live MP4 recording."""
    
    def test_live_mp4_missing_dependencies(self):
        """Test live MP4 recording when dependencies are missing."""
        with patch('cargosim.utils._mp4_available', return_value=(False, "Missing imageio-ffmpeg")):
            with tempfile.TemporaryDirectory() as temp_dir:
                with pytest.raises(RuntimeError, match="MP4 recording requires imageio-ffmpeg"):
                    Recorder(
                        mode="live",
                        folder=temp_dir,
                        fps=30,
                        fmt="mp4"
                    )
    
    @patch('cargosim.utils._mp4_available', return_value=(True, None))
    @patch('imageio.v2.get_writer')
    def test_live_mp4_sync_recording(self, mock_get_writer):
        """Test live MP4 recording in synchronous mode."""
        mock_writer = MagicMock()
        mock_get_writer.return_value = mock_writer
        
        with tempfile.TemporaryDirectory() as temp_dir:
            recorder = Recorder(
                mode="live",
                folder=temp_dir,
                fps=30,
                fmt="mp4",
                async_writer=False
            )
            
            assert recorder.live is True
            assert recorder.fmt == "mp4"
            assert recorder.writer == mock_writer
            assert recorder.queue is None
            assert recorder.thread is None
            
            # Verify writer was configured correctly
            mock_get_writer.assert_called_once()
            call_args = mock_get_writer.call_args
            assert call_args[1]['fps'] == 30
            assert call_args[1]['format'] == "FFMPEG"
    
    @patch('cargosim.utils._mp4_available', return_value=(True, None))
    def test_live_mp4_async_recording(self, mock_mp4_available):
        """Test live MP4 recording in asynchronous mode."""
        with tempfile.TemporaryDirectory() as temp_dir:
            recorder = Recorder(
                mode="live",
                folder=temp_dir,
                fps=30,
                fmt="mp4",
                async_writer=True,
                max_queue=10
            )
            
            assert recorder.live is True
            assert recorder.queue is not None
            assert recorder.thread is not None
            
            # Clean up
            recorder.close()


class TestOfflineRecording:
    """Test offline recording."""
    
    @patch('cargosim.utils._mp4_available', return_value=(True, None))
    @patch('imageio.v2.get_writer')
    def test_offline_mp4_recording(self, mock_get_writer):
        """Test offline MP4 recording."""
        mock_writer = MagicMock()
        mock_get_writer.return_value = mock_writer
        
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            recorder = Recorder(
                mode="offline",
                file_path=temp_path,
                fps=30,
                fmt="mp4"
            )
            
            assert recorder.live is False
            assert recorder.mode == "offline"
            assert recorder.out_path == temp_path
            
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_offline_png_recording(self):
        """Test offline PNG recording."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "frames")
            
            recorder = Recorder(
                mode="offline",
                file_path=output_path,
                fps=30,
                fmt="png"
            )
            
            assert recorder.live is False
            assert recorder.mode == "offline"
            assert recorder.out_path == output_path


class TestRecorderCapture:
    """Test recorder capture functionality."""
    
    def test_live_png_capture(self):
        """Test PNG capture in live mode."""
        with tempfile.TemporaryDirectory() as temp_dir:
            recorder = Recorder(
                mode="live",
                folder=temp_dir,
                fps=30,
                fmt="png",
                async_writer=False
            )
            
            # Mock surface
            mock_surface = MagicMock()
            mock_surface.get_size.return_value = (800, 600)
            
            with patch('pygame.surfarray.array3d') as mock_array3d:
                mock_array3d.return_value = "fake_array"
                
                with patch('imageio.imwrite') as mock_imwrite:
                    recorder.capture(mock_surface)
                    
                    assert recorder.frame_idx == 1
                    mock_imwrite.assert_called_once()
    
    @patch('cargosim.utils._mp4_available', return_value=(True, None))
    @patch('imageio.v2.get_writer')
    def test_live_mp4_capture(self, mock_get_writer):
        """Test MP4 capture in live mode."""
        mock_writer = MagicMock()
        mock_get_writer.return_value = mock_writer
        
        with tempfile.TemporaryDirectory() as temp_dir:
            recorder = Recorder(
                mode="live",
                folder=temp_dir,
                fps=30,
                fmt="mp4",
                async_writer=False
            )
            
            # Mock surface
            mock_surface = MagicMock()
            mock_surface.get_size.return_value = (800, 600)
            
            with patch('pygame.surfarray.array3d') as mock_array3d:
                mock_array3d.return_value = "fake_array"
                
                recorder.capture(mock_surface)
                
                assert recorder.frame_idx == 1
                mock_writer.append_data.assert_called_once_with("fake_array")
    
    def test_async_capture_with_backpressure(self):
        """Test async capture with queue backpressure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            recorder = Recorder(
                mode="live",
                folder=temp_dir,
                fps=30,
                fmt="png",
                async_writer=True,
                max_queue=2,  # Small queue
                drop_on_backpressure=True
            )
            
            # Mock surface
            mock_surface = MagicMock()
            mock_surface.get_size.return_value = (800, 600)
            
            with patch('pygame.surfarray.array3d') as mock_array3d:
                mock_array3d.return_value = "fake_array"
                
                # Fill the queue beyond capacity
                for _ in range(5):
                    recorder.capture(mock_surface)
                
                # Should have dropped some frames
                assert recorder.frames_dropped > 0
            
            # Clean up
            recorder.close()


class TestRecorderClose:
    """Test recorder close functionality."""
    
    def test_live_png_close(self):
        """Test closing live PNG recorder."""
        with tempfile.TemporaryDirectory() as temp_dir:
            recorder = Recorder(
                mode="live",
                folder=temp_dir,
                fps=30,
                fmt="png",
                async_writer=False
            )
            
            result = recorder.close()
            assert result == recorder.out_path
    
    def test_live_async_close(self):
        """Test closing live async recorder."""
        with tempfile.TemporaryDirectory() as temp_dir:
            recorder = Recorder(
                mode="live",
                folder=temp_dir,
                fps=30,
                fmt="png",
                async_writer=True
            )
            
            # Close should wait for thread to finish
            result = recorder.close()
            assert result == recorder.out_path
            
            # Thread should be finished
            if recorder.thread:
                assert not recorder.thread.is_alive()
    
    @patch('cargosim.utils._mp4_available', return_value=(True, None))
    @patch('imageio.v2.get_writer')
    def test_offline_mp4_close_success(self, mock_get_writer):
        """Test closing offline MP4 recorder successfully."""
        mock_writer = MagicMock()
        mock_get_writer.return_value = mock_writer
        
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            recorder = Recorder(
                mode="offline",
                file_path=temp_path,
                fps=30,
                fmt="mp4"
            )
            
            with patch('os.replace') as mock_replace:
                recorder.close(success=True)
                
                mock_writer.close.assert_called_once()
                # Should move temp file to final location
                mock_replace.assert_called_once()
                
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    @patch('cargosim.utils._mp4_available', return_value=(True, None))
    @patch('imageio.v2.get_writer')
    def test_offline_mp4_close_failure(self, mock_get_writer):
        """Test closing offline MP4 recorder with failure."""
        mock_writer = MagicMock()
        mock_get_writer.return_value = mock_writer
        
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            recorder = Recorder(
                mode="offline",
                file_path=temp_path,
                fps=30,
                fmt="mp4"
            )
            
            with patch('os.remove') as mock_remove:
                recorder.close(success=False)
                
                mock_writer.close.assert_called_once()
                # Should remove temp file on failure
                mock_remove.assert_called_once()
                
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestRecorderClassMethods:
    """Test recorder class methods."""
    
    def test_for_live_method(self):
        """Test Recorder.for_live class method."""
        with tempfile.TemporaryDirectory() as temp_dir:
            recorder = Recorder.for_live(
                folder=temp_dir,
                fps=30,
                fmt="png",
                async_writer=False,
                max_queue=64,
                drop_on_backpressure=True
            )
            
            assert recorder.mode == "live"
            assert recorder.fps == 30
            assert recorder.fmt == "png"
            assert recorder.drop_on_backpressure is True
    
    def test_for_offline_method(self):
        """Test Recorder.for_offline class method."""
        with tempfile.NamedTemporaryFile(suffix='.mp4') as temp_file:
            temp_path = temp_file.name
            
            with patch('cargosim.utils._mp4_available', return_value=(True, None)):
                recorder = Recorder.for_offline(
                    file_path=temp_path,
                    fps=30,
                    fmt="mp4"
                )
                
                assert recorder.mode == "offline"
                assert recorder.fps == 30
                assert recorder.fmt == "mp4"


class TestRecorderEdgeCases:
    """Test recorder edge cases and error conditions."""
    
    def test_capture_without_surface(self):
        """Test capture with None surface."""
        with tempfile.TemporaryDirectory() as temp_dir:
            recorder = Recorder(
                mode="live",
                folder=temp_dir,
                fps=30,
                fmt="png"
            )
            
            # Should handle None gracefully
            recorder.capture(None)
            assert recorder.frame_idx == 0  # Should not increment
    
    def test_multiple_close_calls(self):
        """Test multiple close calls."""
        with tempfile.TemporaryDirectory() as temp_dir:
            recorder = Recorder(
                mode="live",
                folder=temp_dir,
                fps=30,
                fmt="png"
            )
            
            # Multiple close calls should not cause errors
            result1 = recorder.close()
            result2 = recorder.close()
            
            assert result1 == result2
    
    def test_finalize_alias(self):
        """Test that finalize is an alias for close."""
        with tempfile.TemporaryDirectory() as temp_dir:
            recorder = Recorder(
                mode="live",
                folder=temp_dir,
                fps=30,
                fmt="png"
            )
            
            close_result = recorder.close()
            
            # Create new recorder for finalize test
            recorder2 = Recorder(
                mode="live",
                folder=temp_dir,
                fps=30,
                fmt="png"
            )
            
            finalize_result = recorder2.finalize()
            
            # Both should return the same type of result
            assert type(close_result) == type(finalize_result)


if __name__ == "__main__":
    pytest.main([__file__])
