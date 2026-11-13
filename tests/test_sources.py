import shutil
import subprocess

import pytest

from instep.sources.base import FileReplay

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")


@pytest.fixture
def clip(tmp_path):
    """Three seconds of ffmpeg's synthetic test pattern, 320x240 at 10 fps."""
    path = tmp_path / "pattern.mp4"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=duration=3:size=320x240:rate=10",
         "-pix_fmt", "yuv420p", str(path)],
        check=True,
    )  # fmt: skip
    return path


def test_file_replay_samples_at_fps_and_scales(clip):
    frames = list(FileReplay(clip, fps=2, width=160).frames())
    assert [f.t_s for f in frames] == [0.0, 0.5, 1.0, 1.5, 2.0, 2.5]
    assert all(f.image.shape == (120, 160, 3) and f.image.dtype == "uint8" for f in frames)


def test_file_replay_still_is_sharper_than_the_stream(clip):
    source = FileReplay(clip, fps=2, width=160, still_width=320)
    assert source.still(1.0).shape == (240, 320, 3)
