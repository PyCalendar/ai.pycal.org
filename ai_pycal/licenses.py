"""The licenses of the software of the site, for the page ``/licenses/``.

The license of the project and the licenses of the code taken over from other projects are read
from ``REUSE.toml`` and ``LICENSES/`` with the REUSE tool; the installed Python packages with
pip-licenses.
"""

from dataclasses import dataclass
from functools import cache
from pathlib import Path

import piplicenses
from reuse.global_licensing import ReuseTOML

ROOT = Path(__file__).resolve().parent.parent
PROJECT_LICENSE = "AGPL-3.0-or-later"
UNKNOWN = "UNKNOWN"  # what pip-licenses says for a field that is missing


@dataclass(frozen=True)
class Package:
    """Software with its version, license and where to read about it.

    Attributes:
        name: The name, or the files of code taken over from another project.
        version: The version installed, or the copyright of code taken over.
        license: The license, such as an SPDX expression.
        url: Where to read about it.
        license_url: Where to read the license, "" if not known.
    """

    name: str
    version: str
    license: str
    url: str
    license_url: str = ""


def license_names(root: Path = ROOT) -> list[str]:
    """The licenses whose texts are in ``LICENSES/``, as REUSE expects them.

    Args:
        root: The project.

    Returns:
        The SPDX identifiers, such as ``AGPL-3.0-or-later``.
    """
    folder = root / "LICENSES"
    return sorted(path.stem for path in folder.glob("*.txt")) if folder.is_dir() else []


def license_file(name: str, root: Path = ROOT) -> Path | None:
    """The text of a license of ``LICENSES/``.

    Args:
        name: The SPDX identifier.
        root: The project.

    Returns:
        The file, None for other names.
    """
    return root / "LICENSES" / f"{name}.txt" if name in license_names(root) else None


def reused(root: Path = ROOT) -> list[Package]:
    """The code taken over from other projects, from the annotations of ``REUSE.toml``.

    Annotations under the license of the project are left out.

    Args:
        root: The project; without ``REUSE.toml`` there are none.

    Returns:
        The files, their copyright and license.
    """
    path = root / "REUSE.toml"
    if not path.is_file():
        return []
    found = []
    for annotation in ReuseTOML.from_file(path, root).annotations:
        expressions = sorted(str(expression) for expression in annotation.spdx_expressions)
        if expressions == [PROJECT_LICENSE]:
            continue
        copyright = ", ".join(sorted(notice.name for notice in annotation.copyright_notices))
        name = ", ".join(sorted(annotation.paths))
        found.append(
            Package(name, copyright, " AND ".join(expressions), "", f"/licenses/{expressions[0]}/")
        )
    return sorted(found, key=lambda package: package.name)


def license_of(entry: dict) -> str:
    """The SPDX expression, the license field, or the license classifiers of a package.

    Args:
        entry: A package as pip-licenses describes it.

    Returns:
        The license, "see the package" if none is given.

    Examples:
        >>> license_of({"license_expression": "MIT"})
        'MIT'
        >>> license_of({"license_expression": "UNKNOWN", "license": "BSD"})
        'BSD'
        >>> license_of({})
        'see the package'
    """
    expression = entry.get("license_expression", UNKNOWN)
    if expression != UNKNOWN:
        return expression
    text = entry.get("license", UNKNOWN).strip()
    if text != UNKNOWN and text and "\n" not in text and len(text) < 80:
        return text
    return ", ".join(entry.get("license_classifier", [])) or "see the package"


@cache
def installed() -> dict[str, dict]:
    """The installed Python packages as pip-licenses reads them, by lower case name.

    Returns:
        The entries of pip-licenses, with the texts of their license files.
    """
    arguments = piplicenses.create_parser().parse_args(
        ["--from=mixed", "--with-system", "--with-urls", "--with-license-file", "--no-license-path"]
    )
    found: dict[str, dict] = {}
    for entry in piplicenses.get_packages(arguments):
        found.setdefault(str(entry["name"]).lower(), entry)
    return found


def package_license_text(name: str) -> str | None:
    """The text of the license file of an installed package.

    Args:
        name: The name of the package, in any case.

    Returns:
        The text, None if the package is not installed or ships no license file.
    """
    entry = installed().get(name.lower())
    if entry is None or entry.get("licensetext", UNKNOWN) == UNKNOWN:
        return None
    return entry["licensetext"]


@cache
def packages() -> list[Package]:
    """The installed Python packages, by name, linked to the texts of their licenses.

    Returns:
        The packages, read by pip-licenses.
    """
    found = []
    for key, entry in installed().items():
        url = entry.get("home-page", UNKNOWN)
        if not url.startswith(("http://", "https://")):
            url = f"https://pypi.org/project/{entry['name']}/"
        text_url = f"/licenses/packages/{key}/" if package_license_text(key) else ""
        found.append(Package(entry["name"], entry["version"], license_of(entry), url, text_url))
    return sorted(found, key=lambda package: package.name.lower())
