"""Write the build information into ai_pycal/version.json, before the image is built.

The commit, its message and time come from git; in GitHub Actions also the tag and the link
to the run. The About page shows them (``ai_pycal/build_info.py``). Only the standard library
is used, so that it runs before the packages are installed.
"""

import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "ai_pycal" / "version.json"


def git(*arguments: str) -> str:
    """The output of git in the checkout, or "" without git.

    Args:
        *arguments: The arguments of git.

    Returns:
        The output without the line break at the end.
    """
    try:
        found = subprocess.run(
            ["git", "-C", str(ROOT), *arguments],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return found.stdout.strip()


def version(environ: dict[str, str]) -> str:
    """The version: the release tag, else what git describes, else "development".

    Args:
        environ: The environment, such as ``os.environ``.

    Returns:
        The version, such as ``1.2.3`` or ``v0.1.0-4-g3f7dc48``.
    """
    if environ.get("GITHUB_REF_TYPE") == "tag":
        return environ.get("GITHUB_REF_NAME", "").removeprefix("v")
    return git("describe", "--tags", "--always") or "development"


def build_info(environ: dict[str, str]) -> dict[str, str]:
    """The build information of this checkout.

    Args:
        environ: The environment, such as ``os.environ``.

    Returns:
        version, built, commit, commit_full, message, committed, tag and build_url.
    """
    commit = environ.get("GITHUB_SHA") or git("rev-parse", "HEAD")
    build_url = ""
    if environ.get("GITHUB_RUN_ID"):
        server = environ.get("GITHUB_SERVER_URL", "https://github.com")
        repository = environ.get("GITHUB_REPOSITORY", "PyCalendar/ai.pycal.org")
        build_url = f"{server}/{repository}/actions/runs/{environ['GITHUB_RUN_ID']}"
    return {
        "version": version(environ),
        "built": datetime.now(UTC).isoformat(timespec="seconds"),
        "commit": commit[:7],
        "commit_full": commit,
        "message": git("log", "-1", "--format=%s", commit) if commit else "",
        "committed": git("log", "-1", "--format=%cI", commit) if commit else "",
        "tag": environ.get("GITHUB_REF_NAME", "")
        if environ.get("GITHUB_REF_TYPE") == "tag"
        else "",
        "build_url": build_url,
    }


def main() -> None:
    """Write ai_pycal/version.json, or the file given as argument."""
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else TARGET
    info = build_info(dict(os.environ))
    target.write_text(json.dumps(info, indent=2) + "\n")
    print(f"Version set: {info['version']} {info['commit']} {info['message']}")


if __name__ == "__main__":
    main()
