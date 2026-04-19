import subprocess
import json
from static_ffmpeg import run


def _ffprobe_path() -> str:
    """Return the path to the ffprobe executable managed by static_ffmpeg.

    Returns:
        The absolute path to the ffprobe binary (str).
    """
    _, ffprobe = run.get_or_fetch_platform_executables_else_raise()
    return ffprobe


def probe_streams(path: str) -> tuple[list[dict], dict]:
    """Probe a media file and return its streams and format metadata.

    Args:
        path: Absolute or relative path to the media file (str).

    Returns:
        A tuple of (streams, format) where streams is a list of ffprobe stream dicts
        and format is the ffprobe format dict (tuple[list[dict], dict]).
    """
    if path.endswith(".srt"):
        stream = {
            "index": 0,
            "codec_name": "subrip",
            "codec_type": "subtitle",
            "tags": {"language": ""}
        }
        return [stream], {}
    else:
        result = subprocess.run(
            [
                _ffprobe_path(),
                "-v", "quiet",
                "-print_format", "json",
                "-show_streams",
                "-show_format",
                path,
            ],
            capture_output=True,
            text=True,
        )
        data = json.loads(result.stdout)
        return data.get("streams", []), data.get("format", {})
