==============================
Change the colors and the icon
==============================

The site uses the colors of the Python Calendaring Ecosystem: the blue and the
yellow of its logo. The people who run a site can change every color, the icon
and the name, with settings in ``.env``.

Colors
======

Each color has a setting ``COLOR_<NAME>`` for the light pages and
``COLOR_DARK_<NAME>`` for the dark pages, which browsers show when the system
is dark or when the visitor chooses them (see :ref:`theme-switch`). The values are hexadecimal colors such as ``#3b79aa`` or ``#fd0``.

.. list-table::
   :header-rows: 1

   * - Setting
     - Default
     - Used for
   * - ``COLOR_PRIMARY``
     - ``#2b5b84``
     - links and buttons
   * - ``COLOR_PRIMARY_HOVER``
     - ``#1e3f5c``
     - links and buttons under the pointer
   * - ``COLOR_BRAND``
     - ``#3b79aa``
     - the blue of the logo
   * - ``COLOR_ACCENT``
     - ``#ffd43b``
     - the yellow line below the menu and the sign in button
   * - ``COLOR_ACCENT_TEXT``
     - ``#1b1f24``
     - text on the accent color
   * - ``COLOR_NAV``
     - ``#1e3f5c``
     - the background of the menu
   * - ``COLOR_NAV_TEXT``
     - ``#ffffff``
     - the text of the menu
   * - ``COLOR_SURFACE``
     - ``#ffffff``
     - the background of the pages
   * - ``COLOR_SURFACE_TINT``
     - ``#eef4f9``
     - the background of highlighted parts
   * - ``COLOR_TEXT``
     - ``#1b1f24``
     - the text
   * - ``COLOR_TEXT_MUTED``
     - ``#4f5b66``
     - less important text
   * - ``COLOR_BORDER``
     - ``#c5d3e0``
     - lines and borders
   * - ``COLOR_SUCCESS``
     - ``#1d6b33``
     - signed agreements and added lines
   * - ``COLOR_WARNING``
     - ``#7a5300``
     - agreements to sign
   * - ``COLOR_DANGER``
     - ``#a3242f``
     - errors and removed lines

For example:

.. code-block:: shell

   COLOR_PRIMARY=#7a1f5c
   COLOR_NAV=#4a1238
   COLOR_DARK_PRIMARY=#f0a8d8

A wrong value stops the start of the site with
:class:`~ai_pycal.errors.configuration.InvalidColor` or
:class:`~ai_pycal.errors.configuration.UnknownColor`. Check the contrast of
text and background, for example with the contrast checker of the developer
tools of the browser.

.. _theme-switch:

Light and dark pages
====================

The menu of every page has a button with the icon of the current colors, like
the switch of this documentation: a half circle for *As the system*, a sun for
*Light* and a moon for *Dark*. It opens a dropdown with the three choices. It
works without JavaScript: the dropdown is a ``<details>`` element and the
choices are the buttons of a form sent to ``/theme/``,
which keeps *Light* or *Dark* for a year in the cookie ``theme`` and returns to
the page. *As the system* removes the cookie, so that the browser chooses the
light or the dark colors again. The site ignores unknown values of the cookie.

More style
==========

``EXTRA_CSS_URL`` adds a style sheet after that of the site, to change more
than the colors.

Icon
====

``FAVICON_FILE`` is the path of a PNG, ICO or SVG file in the container. Put it
in the volume of the data:

.. code-block:: shell

   cp my-icon.png data/favicon.png
   echo FAVICON_FILE=/app/data/favicon.png >> .env

The icon is shown in the menu and as icon of the browser tab, at
``/favicon.ico``. The default is the icon of pycal.

Name
====

``SITE_NAME`` is shown in the menu, in the titles and in the names of the
checks of the pull requests (``STATUS_CONTEXT``).
