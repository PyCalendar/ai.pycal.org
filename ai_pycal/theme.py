"""The colors of the site, which the people who run it can change with ``COLOR_...`` settings."""

import re
from dataclasses import dataclass, field

from ai_pycal.errors import InvalidColor, UnknownColor

HEX = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")

# The pycal colors: the blue and the yellow of the logo of the Python Calendaring Ecosystem.
LIGHT = {
    "primary": "#2b5b84",  # buttons and links: contrast 7.0 on white
    "primary_hover": "#1e3f5c",
    "brand": "#3b79aa",  # the blue of the logo
    "accent": "#ffd43b",  # the yellow of the logo
    "accent_text": "#1b1f24",
    "nav": "#1e3f5c",
    "nav_text": "#ffffff",
    "surface": "#ffffff",
    "surface_tint": "#eef4f9",
    "text": "#1b1f24",
    "text_muted": "#4f5b66",
    "border": "#c5d3e0",
    "success": "#1d6b33",
    "warning": "#7a5300",
    "danger": "#a3242f",
}
DARK = {
    "primary": "#8fbbe0",
    "primary_hover": "#c6dcef",
    "brand": "#3b79aa",
    "accent": "#ffd43b",
    "accent_text": "#1b1f24",
    "nav": "#0d1b28",
    "nav_text": "#ffffff",
    "surface": "#111820",
    "surface_tint": "#1b2733",
    "text": "#e6edf3",
    "text_muted": "#a8b5c2",
    "border": "#34475a",
    "success": "#7fd18f",
    "warning": "#f2c55c",
    "danger": "#f1aeb5",
}


@dataclass(frozen=True)
class Theme:
    """The colors of the light and the dark pages."""

    light: dict[str, str] = field(default_factory=lambda: dict(LIGHT))
    dark: dict[str, str] = field(default_factory=lambda: dict(DARK))

    @classmethod
    def from_environment(cls, environ: dict[str, str]) -> "Theme":
        """The theme with the colors of ``COLOR_<NAME>`` and ``COLOR_DARK_<NAME>``.

        Args:
            environ: The environment, such as ``os.environ``.

        Returns:
            The theme.

        Raises:
            InvalidColor: A value is not a color such as ``#3b79aa``.
            UnknownColor: The name is not a color of the theme.

        Examples:
            >>> theme = Theme.from_environment({"COLOR_PRIMARY": "#123456"})
            >>> theme.light["primary"], theme.dark["primary"]
            ('#123456', '#8fbbe0')
            >>> Theme.from_environment({"COLOR_DARK_ACCENT": "#abc"}).dark["accent"]
            '#abc'
        """
        light, dark = dict(LIGHT), dict(DARK)
        for key, value in environ.items():
            if not key.startswith("COLOR_"):
                continue
            name = key.removeprefix("COLOR_").lower()
            colors = light
            if name.startswith("dark_"):
                name, colors = name.removeprefix("dark_"), dark
            if name not in LIGHT:
                raise UnknownColor(f"{key}; known: {', '.join(sorted(LIGHT))}")
            if not HEX.match(value.strip()):
                raise InvalidColor(f"{key}={value!r}")
            colors[name] = value.strip()
        return cls(light, dark)

    @staticmethod
    def css(colors: dict[str, str]) -> str:
        """The colors as CSS custom properties.

        Args:
            colors: The colors by name.

        Returns:
            The declarations, such as ``--primary: #2b5b84;``.

        Examples:
            >>> Theme.css({"text_muted": "#000"})
            '--text-muted: #000;'
        """
        return " ".join(f"--{name.replace('_', '-')}: {value};" for name, value in colors.items())

    def stylesheet(self) -> str:
        """The CSS of the colors: light, and dark when the system asks for it.

        Returns:
            The CSS, for a ``<style>`` element.
        """
        return (
            f":root {{ {self.css(self.light)} color-scheme: light dark; }}\n"
            f"@media (prefers-color-scheme: dark) {{ :root {{ {self.css(self.dark)} }} }}"
        )
