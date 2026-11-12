"""docker/set_version.py writes the build information that the About page shows."""

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT / "docker"))
import set_version  # noqa: E402


def test_a_release_in_github_actions():
    info = set_version.build_info(
        {
            "GITHUB_SHA": "4cbfd3edf2dcf1976b57ecf2c71ab35a9e0ccbdc",
            "GITHUB_REF_TYPE": "tag",
            "GITHUB_REF_NAME": "v1.2.3",
            "GITHUB_RUN_ID": "43245171349",
            "GITHUB_REPOSITORY": "PyCalendar/sign.pycal.org",
            "GITHUB_SERVER_URL": "https://github.com",
        }
    )
    assert info["version"] == "1.2.3"
    assert info["tag"] == "v1.2.3"
    assert info["commit"] == "4cbfd3e"
    assert info["build_url"] == (
        "https://github.com/PyCalendar/sign.pycal.org/actions/runs/43245171349"
    )
    assert info["built"].endswith("+00:00")


def test_a_local_build_reads_git(tmp_path):
    target = tmp_path / "version.json"
    local = {key: value for key, value in os.environ.items() if not key.startswith("GITHUB_")}
    subprocess.run(
        [sys.executable, str(ROOT / "docker" / "set_version.py"), str(target)],
        check=True,
        env=local,
    )
    info = json.loads(target.read_text())
    head = subprocess.run(
        ["git", "-C", str(ROOT), "log", "-1", "--format=%H%n%s"], capture_output=True, text=True
    ).stdout.split("\n")
    assert info["commit_full"] == head[0]
    assert info["message"] == head[1]
    assert info["committed"]
    assert info["build_url"] == ""
    assert info["tag"] == ""


def test_the_version_file_is_not_committed_but_built_into_the_image():
    assert "/ai_pycal/version.json" in (ROOT / ".gitignore").read_text()
    assert "version.json" not in (ROOT / ".dockerignore").read_text()
    makefile = (ROOT / "Makefile").read_text()
    assert "docker-build: version" in makefile
    assert "run: make version" in (ROOT / ".github" / "workflows" / "tests.yml").read_text()
