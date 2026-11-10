"""Errors of the settings of the site, met by the people who run it.

The site does not start with them; the message names the setting. All settings
are listed in :doc:`/reference/settings`.
"""

from django.utils.translation import gettext_lazy as _

from .base import AgreementError


class ConfigurationError(AgreementError):
    """A setting of the site is invalid.

    Fix the setting in the environment, such as the file ``.env``, and start the
    site again. All settings are listed in :doc:`/reference/settings`.
    """

    title = _("A setting of the site is invalid")
    status = 500
    guide = "reference/settings.html"
    guide_title = _("Settings")


class InvalidColor(ConfigurationError):
    """A color of the theme is not a color.

    The colors of the site are set with ``COLOR_...`` settings, such as
    ``COLOR_PRIMARY=#3b79aa``. Use ``#`` and three or six hexadecimal digits.
    See :doc:`/how-to/brand`.
    """

    title = _("A color of the theme is invalid")
    guide = "how-to/brand.html"
    guide_title = _("Change the colors and the icon")


class UnknownColor(ConfigurationError):
    """A ``COLOR_...`` setting names a color the theme does not have.

    The names of the colors are listed in :doc:`/how-to/brand`, such as
    ``COLOR_PRIMARY`` or ``COLOR_DARK_PRIMARY``. Check the spelling.
    """

    title = _("The theme has no such color")
    guide = "how-to/brand.html"
    guide_title = _("Change the colors and the icon")


class FaviconNotFound(ConfigurationError):
    """The file of ``FAVICON_FILE`` does not exist.

    ``FAVICON_FILE`` is the path of a PNG, ICO or SVG file inside the container,
    such as ``/app/data/favicon.png`` in the volume of the data. See
    :doc:`/how-to/brand`.
    """

    title = _("The favicon was not found")
    guide = "how-to/brand.html"
    guide_title = _("Change the colors and the icon")


class UnsupportedFavicon(ConfigurationError):
    """The file of ``FAVICON_FILE`` is not a PNG, ICO or SVG file.

    Browsers show these formats as icon of the page. Convert the icon and name
    the file with its extension: ``.png``, ``.ico`` or ``.svg``.
    """

    title = _("The favicon has an unsupported format")
    guide = "how-to/brand.html"
    guide_title = _("Change the colors and the icon")
