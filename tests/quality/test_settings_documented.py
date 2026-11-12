"""Every environment variable is documented on the reference page and in .env.example."""

import re
from pathlib import Path

ROOT = Path(__file__).parents[2]
REFERENCE = (ROOT / "docs" / "reference" / "settings.rst").read_text()
EXAMPLE = (ROOT / ".env.example").read_text()
# set by the image or the tools, not by the people who run the site
INTERNAL = {"PATH", "PYTHONUNBUFFERED", "UV_PROJECT_ENVIRONMENT", "DJANGO_SETTINGS_MODULE"}
# older names, still read and documented, but not offered in .env.example
OLDER_NAMES = {"FAVICON_FILE"}


def read_variables() -> set[str]:
    """The environment variables that the site, the image and the build read."""
    names = set()
    settings = (ROOT / "ai_pycal" / "settings.py").read_text()
    names |= set(re.findall(r"env(?:\.\w+)?\(\s*\"([A-Z][A-Z0-9_]+)\"", settings))
    names |= set(re.findall(r"kept_secret\(\"([A-Z][A-Z0-9_]+)\"\)", settings))
    names |= set(re.findall(r"^ENV ([A-Z][A-Z0-9_]+)=", (ROOT / "Dockerfile").read_text(), re.M))
    for script in ("docker/start-service.sh", "docker/healthcheck.py", "docker/set_version.py"):
        text = (ROOT / script).read_text()
        names |= set(re.findall(r"\$\{?([A-Z][A-Z0-9_]+)", text))
        names |= set(re.findall(r"environ(?:\.get)?[\(\[]\"([A-Z][A-Z0-9_]+)\"", text))
        names |= set(re.findall(r"environ\.get\(\"([A-Z][A-Z0-9_]+)\"", text))
    return names - INTERNAL


def test_the_variables_are_found():
    names = read_variables()
    assert {"SITE_URL", "SECRET_KEY", "WORKERS", "GITHUB_RUN_ID", "FOOTER_LINKS"} <= names


def test_every_variable_is_on_the_reference_page():
    missing = [name for name in sorted(read_variables()) if f"``{name}``" not in REFERENCE]
    assert not missing


def test_every_setting_of_the_site_is_in_the_example():
    build = set(re.findall(r"``(GITHUB_[A-Z_]+)``", REFERENCE.split("9. Build information")[1]))
    missing = [
        name
        for name in sorted(read_variables() - build - OLDER_NAMES)
        if not re.search(rf"^#? ?{name}=", EXAMPLE, re.MULTILINE)
    ]
    assert not missing
    assert "COLOR_" in EXAMPLE


def test_the_example_links_to_existing_sections():
    for anchor in re.findall(r"settings\.html#([\w-]+)", EXAMPLE):
        assert f".. _{anchor}:" in REFERENCE, anchor


def test_the_example_follows_the_order_of_the_reference():
    sections = re.findall(r"^\d+\. (.+)\n=+$", REFERENCE, re.MULTILINE)
    headings = re.findall(r"^######## \d+\. (.+?)(?: \(required\))? ########$", EXAMPLE, re.M)
    assert headings == sections[: len(headings)]
