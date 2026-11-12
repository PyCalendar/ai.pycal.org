"""The settings that the site writes into its volume: ``DATA_DIR/.env``.

When the GitHub App is registered on the site (``/setup/github-app/``), its credentials are
written there. The settings read the file at every start; a variable of the environment always
takes precedence, an empty one counts as unset. Only the standard library is used, because the
settings load it before Django is set up.
"""

import os
from collections.abc import Mapping, MutableMapping
from pathlib import Path

HEADER = (
    "# Written by the site when its GitHub App was registered (/setup/github-app/).\n"
    "# Variables of the environment take precedence over these values.\n"
)


def read(path: Path) -> dict[str, str]:
    """The settings of a ``.env`` file: ``NAME=value`` lines; ``#`` starts a comment.

    Args:
        path: The file; a missing file has no settings.

    Returns:
        The values by name.
    """
    if not path.is_file():
        return {}
    values = {}
    for line in path.read_text().splitlines():
        name, separator, value = line.strip().partition("=")
        if separator and name and not name.startswith("#"):
            values[name.strip()] = value.strip()
    return values


def load(path: Path, environ: MutableMapping[str, str]) -> list[str]:
    """Put the settings of the file into the environment, where they are not set.

    Args:
        path: The file, such as ``DATA_DIR/.env``.
        environ: The environment, such as ``os.environ``.

    Returns:
        The names that were taken from the file.
    """
    return load_values(read(path), environ)


def load_values(values: Mapping[str, str], environ: MutableMapping[str, str]) -> list[str]:
    """Put settings into the environment, where they are not set.

    Args:
        values: The values by name.
        environ: The environment, such as ``os.environ``.

    Returns:
        The names that were taken.

    Examples:
        >>> environ = {"A": "set", "B": ""}
        >>> load_values({"A": "file", "B": "file", "C": "file"}, environ), environ
        (['B', 'C'], {'A': 'set', 'B': 'file', 'C': 'file'})
    """
    taken = []
    for name, value in values.items():
        if not environ.get(name):
            environ[name] = value
            taken.append(name)
    return taken


def write(path: Path, values: Mapping[str, str]) -> None:
    """Add settings to the file, readable only by the site.

    Args:
        path: The file, such as ``DATA_DIR/.env``; it is created if missing.
        values: The values by name; existing lines are kept.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text() if path.is_file() else HEADER
    if existing and not existing.endswith("\n"):
        existing += "\n"
    lines = "".join(f"{name}={value}\n" for name, value in values.items())
    write_private(path, existing + lines)


def write_private(path: Path, text: str) -> None:
    """Write a file that only the owner can read, such as a key.

    Args:
        path: The file.
        text: The content.
    """
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w") as file:
        file.write(text)
    path.chmod(0o600)
