==========
Contribute
==========

Contributions are welcome. People who use AI follow the `AI policy of icalendar
and the Python Calendaring Ecosystem
<https://icalendar.readthedocs.io/en/latest/contribute/index.html>`_; the prompts
are recorded with `ai-prompt-auto-commit
<https://github.com/PyCalendar/ai-prompt-auto-commit>`_.

Set up the development environment as in :doc:`how-to/develop`. Every change
people notice has a news fragment in :file:`news/`, such as
``news/+name.feature``, that ``towncrier`` collects into :doc:`changelog`.

.. _translate:

Translate
=========

The site speaks English, German and Spanish. A visitor first gets the language
their browser asks for, and the menu with the globe next to the colors changes
it. The menu names each language in itself, such as *Deutsch*, and the choice is
kept for a year in the cookie ``django_language``.

The texts of the site are in :file:`ai_pycal/locale/<language>/LC_MESSAGES/`:
:file:`django.po` holds them for people, :file:`django.mo` compiled for the
site. Both are in the repository, so the image needs no gettext.

Improve a translation
---------------------

#. Find the English text, the ``msgid``, in :file:`django.po` of the language,
   and change its ``msgstr``. Keep placeholders such as ``%(count)d`` or
   ``%(site_name)s`` and HTML such as ``<code>`` as they are.
#. Run ``make messages``. It collects the texts of the code and the templates,
   merges them into every :file:`django.po` and compiles :file:`django.mo`.
   It uses gettext if it is installed, such as with ``apt install gettext``,
   and otherwise runs gettext in Docker.
#. Run ``make test``. The tests check that every text of every language is
   translated, that none is marked ``fuzzy`` and that :file:`django.mo`
   matches :file:`django.po`.

After a change of a text in the code, ``make messages`` marks the old
translation ``#, fuzzy`` or adds an empty ``msgstr``: translate it and remove
the ``fuzzy`` line.

Add a language
--------------

#. Add the language to ``LANGUAGES`` in :file:`ai_pycal/settings.py`, such as
   ``("fr", "Français")``.
#. Add ``-l fr`` to ``MESSAGES`` in the :file:`Makefile` and run
   ``make messages``.
#. Translate :file:`ai_pycal/locale/fr/LC_MESSAGES/django.po`. Check that its
   header has ``Language: fr`` and the ``Plural-Forms`` of the language.
#. Add the language to the test :file:`tests/site/test_languages.py`.

Write texts in the code with ``gettext`` (``_("…")``) and in templates with
``{% translate %}`` or ``{% blocktranslate %}``. A text without them stays in
English.

Translate an agreement
----------------------

The agreements are not translated here but in their projects: see
:ref:`agreement-translations`.

.. _license:

License
=======

The code is under the `AGPL-3.0-or-later
<https://github.com/PyCalendar/sign.pycal.org/blob/main/LICENSE>`_. Files taken
from other projects keep their licenses, such as the icon of pycal under
CC-BY-SA-4.0; :file:`REUSE.toml` lists them and :file:`LICENSES/` has their
texts. The page `Licenses <https://sign.pycal.org/licenses/>`_ of the site also
shows the licenses of the Python packages it uses.
