======
Errors
======

The site shows an error with its title, what happened and a link to its
description here. Each description says what the error means and how to solve
it. The webhooks answer GitHub with the same name, title and link, shown in the
recent deliveries of the GitHub App. An error the site does not know is shown
as :class:`~ai_pycal.errors.base.UnexpectedError`: please report it.

Pages of HTTP errors
====================

Pages that do not exist (404), pages a visitor may not open (403), requests
the site cannot understand (400), forms sent without the cookie of the site or
left open too long (403) and failures of the site (500) have pages in the
design of the site. Each shows the status, what happened, what to do, a link
back to the start and one to report a bug. If the page of a failure cannot be
shown with the menu, for example because the database is down, it is shown
without the menu in the same colors; if even that fails, as plain text. The
views are in ``ai_pycal/views/errors.py``.

The configuration file
======================

.. automodule:: ai_pycal.errors.config_file
   :members:
   :show-inheritance:

Signing
========

.. automodule:: ai_pycal.errors.signing
   :members:
   :show-inheritance:

Setting up repositories
=======================

.. automodule:: ai_pycal.errors.setup
   :members:
   :show-inheritance:

GitHub
======

.. automodule:: ai_pycal.errors.github
   :members:
   :show-inheritance:

Webhooks
========

.. automodule:: ai_pycal.errors.webhooks
   :members:
   :show-inheritance:

Settings of the site
====================

.. automodule:: ai_pycal.errors.configuration
   :members:
   :show-inheritance:

All errors
==========

.. automodule:: ai_pycal.errors.base
   :members:
   :show-inheritance:
   :exclude-members: docs_url, guide_url, code

Policy choices
==============

.. automodule:: ai_pycal.errors.choices
   :members:
   :show-inheritance:
