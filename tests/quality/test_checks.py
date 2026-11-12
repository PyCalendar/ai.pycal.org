"""The checks of the workflows (zizmor) and of the prose (Vale) are set up and stay strict."""

import configparser
import re
from pathlib import Path

ROOT = Path(__file__).parents[2]
USES = re.compile(r"^\s*-?\s*uses:\s*(\S+)", re.MULTILINE)


def test_every_action_is_pinned_to_a_commit():
    workflows = sorted((ROOT / ".github" / "workflows").glob("*.yml"))
    assert workflows
    for workflow in workflows:
        for action in USES.findall(workflow.read_text()):
            assert re.fullmatch(r"[\w.-]+/[\w./-]+@[0-9a-f]{40}", action), (workflow, action)


def test_ci_runs_the_prose_and_workflow_checks():
    text = (ROOT / ".github" / "workflows" / "tests.yml").read_text()
    assert "make prose" in text
    assert "make workflows" in text
    makefile = (ROOT / "Makefile").read_text()
    assert re.search(r"^prose:", makefile, re.MULTILINE)
    assert re.search(r"^workflows:", makefile, re.MULTILINE)


def test_vale_checks_the_documentation_with_the_project_words():
    config = configparser.ConfigParser()
    config.read_string("[root]\n" + (ROOT / ".vale.ini").read_text())
    vocabulary = config["root"]["Vocab"]
    words = ROOT / ".vale" / "styles" / "config" / "vocabularies" / vocabulary / "accept.txt"
    assert "pycal" in words.read_text().split()
    assert "Vale" in config["*.{rst,md}"]["BasedOnStyles"]


def test_the_tests_run_on_all_processors():
    makefile = (ROOT / "Makefile").read_text()
    assert re.search(r"^JOBS\s*\?=\s*auto$", makefile, re.MULTILINE)
    assert 'pytest -n "$(JOBS)"' in makefile
    assert "pytest-xdist" in (ROOT / "pyproject.toml").read_text()


def test_the_image_is_pushed_after_all_checks_and_deployed():
    text = (ROOT / ".github" / "workflows" / "tests.yml").read_text()
    text = text.split("\njobs:\n")[1]
    jobs = re.findall(r"^  ([\w-]+):\n", text, re.MULTILINE)
    push = text.split("\n  push:\n")[1].split("\n  deploy:\n")[0]
    needed = set(re.search(r"needs: \[(.*)\]", push).group(1).replace(" ", "").split(","))
    assert needed == set(jobs) - {"push", "deploy"}
    assert "if: github.event_name == 'push'" in push
    assert "platforms: linux/amd64,linux/arm64" in push
    assert "make docker-scan" in text
    deploy = text.split("\n  deploy:\n")[1]
    assert "needs: [push]" in deploy
    assert "secrets.SENCHO_TOKEN" in deploy
    assert "/api/stacks/${SENCHO_STACK}/update" in deploy


def test_compose_uses_the_pushed_image():
    compose = (ROOT / "docker-compose.yml").read_text()
    assert "image: ghcr.io/pycalendar/ai.pycal.org:latest" in compose
    assert "./data:/app/data" in compose
