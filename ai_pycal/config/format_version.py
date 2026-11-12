"""The version of the format of a configuration file."""

import re
from dataclasses import dataclass

from ai_pycal.errors import ConfigVersionInvalid, ConfigVersionUnsupported

VERSION = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


@dataclass(frozen=True, order=True)
class FormatVersion:
    """A version of the format, such as 1.0.0, compared by its numbers."""

    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, value: object) -> "FormatVersion":
        """The version of a configuration file.

        Args:
            value: The value of ``version:``.

        Returns:
            The version.

        Raises:
            ConfigVersionInvalid: It is not three numbers with dots.

        Examples:
            >>> FormatVersion.parse("1.0.0")
            FormatVersion(major=1, minor=0, patch=0)
            >>> FormatVersion.parse("1.0")
            Traceback (most recent call last):
            ...
            ai_pycal.errors.config_file.ConfigVersionInvalid: version: '1.0', expected such as 1.0.0
        """
        match = VERSION.match(str(value).strip()) if isinstance(value, str) else None
        if not match:
            raise ConfigVersionInvalid(f"version: {value!r}, expected such as 1.0.0")
        return cls(*(int(part) for part in match.groups()))

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def check_supported(self, newest: "FormatVersion") -> bool:
        """Whether this site can read a file of this version.

        Args:
            newest: The newest version the site reads.

        Returns:
            True if the file is newer than *newest* within the same major version: keys
            this site does not know are then ignored instead of refused.

        Raises:
            ConfigVersionUnsupported: The major version differs.

        Examples:
            >>> FormatVersion(1, 2, 0).check_supported(FormatVersion(1, 0, 0))
            True
            >>> FormatVersion(1, 0, 0).check_supported(FormatVersion(1, 0, 0))
            False
        """
        if self.major not in (1, newest.major):
            raise ConfigVersionUnsupported(
                f"version: {self}; this site reads {newest.major}.x.x up to {newest}"
            )
        return self.minor > (0 if self.major == 1 else newest.minor)


SUPPORTED = FormatVersion(2, 1, 0)  # 2.1.0: pr.unsigned-labels
