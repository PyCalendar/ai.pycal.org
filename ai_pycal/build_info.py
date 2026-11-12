"""The build information of the version that runs, for the About page.

In the image it is read from ``ai_pycal/version.json``, which ``docker/set_version.py`` writes
before the build; in a checkout it comes from git.
"""

import json
import subprocess
from datetime import datetime
from functools import cache
from pathlib import Path

HERE = Path(__file__).parent
VERSION_FILE = HERE / "version.json"
FIELDS = ("version", "built", "commit", "commit_full", "message", "committed", "tag", "build_url")


def from_git() -> dict[str, str]:
    """The build information of the checkout, without a build.

    Returns:
        The commit, its message and time; empty values without git.
    """
    try:
        found = subprocess.run(
            ["git", "-C", str(HERE), "log", "-1", "--format=%H%n%cI%n%s"],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
        commit, committed, message = (found.stdout.splitlines() + ["", "", ""])[:3]
    except (OSError, subprocess.SubprocessError):
        commit = committed = message = ""
    return {
        "version": "development",
        "commit": commit[:7],
        "commit_full": commit,
        "message": message,
        "committed": committed,
    }


def parse_time(value: str) -> datetime | None:
    """A time of the build information.

    Args:
        value: An ISO 8601 time such as ``2026-11-12T15:10:54+01:00``, or "".

    Returns:
        The time, or None.

    Examples:
        >>> parse_time("2026-11-12T15:10:54+01:00").isoformat()
        '2026-11-12T15:10:54+01:00'
        >>> parse_time("") is None
        True
    """
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


@cache
def get(source_url: str) -> dict:
    """The build information, read once, with the links to the code.

    Args:
        source_url: The address of the repository of the code.

    Returns:
        The fields of :data:`FIELDS`, ``built_at`` and ``committed_at`` as times, and
        ``commit_url`` and ``code_url``.
    """
    info = dict.fromkeys(FIELDS, "")
    if VERSION_FILE.exists():
        info.update(json.loads(VERSION_FILE.read_text()))
    else:
        info.update(from_git())
    info["built_at"] = parse_time(info["built"])
    info["committed_at"] = parse_time(info["committed"])
    source_url = source_url.rstrip("/")
    commit = info["commit_full"]
    info["commit_url"] = f"{source_url}/commit/{commit}" if commit else ""
    reference = info["tag"] or commit
    info["code_url"] = f"{source_url}/tree/{reference}" if reference else source_url
    return info
