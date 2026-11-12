========
Settings
========

The site is configured with environment variables, such as in ``.env``.
:file:`.env.example` lists all of them in the same order as this page, the
most important first, each with a comment and a link here. For a local test
setup, copy :file:`.env.development.example` to ``.env``, fill in the GitHub
App credentials and restart ``make run``. See :ref:`the development
configuration <development-configuration>`.

A wrong value stops the start of the site with an error that names the
setting (:doc:`/reference/errors`). Change ``.env`` and start the site again.

.. _settings-address:

1. The address of the site
==========================

Every deployment sets these three. They must match the address that people
and GitHub use.

``SITE_URL``
   The address of the site, without ``/`` at the end, such as
   ``https://ai.pycal.org``. The checks of the pull requests, the emails and
   the GitHub App link to it, and the sign-in callback uses its scheme.
   Default ``https://ai.pycal.org``; ``make run`` uses
   ``http://localhost:5000``.
``ALLOWED_HOSTS``
   The host names of the site, comma separated, such as ``ai.pycal.org``.
   Requests for other hosts are refused. The health check of the container
   sends the first one. Default ``*`` (any host); ``make run`` derives it from
   ``SITE_URL``.
``CSRF_TRUSTED_ORIGINS``
   The address of the site with its scheme, such as ``https://ai.pycal.org``,
   comma separated. Forms sent from other origins are refused. Default none;
   ``make run`` derives it from ``SITE_URL``.

.. _settings-github-app:

2. The GitHub App
=================

Without these, nobody can sign in and no repository can be added. Create the
app as :doc:`/how-to/github-app` describes; it shows where each value is.

``GITHUB_APP_ID``
   The numeric id of the app.
``GITHUB_APP_SLUG``
   The name of the app in its address, such as ``ai-pycal-org`` in
   ``https://github.com/apps/ai-pycal-org``. The Setup page links there to
   install the app.
``GITHUB_CLIENT_ID``, ``GITHUB_SECRET``
   The client id and a client secret of the app, for signing in with GitHub and
   renewing the tokens of the people.
``GITHUB_WEBHOOK_SECRET``
   The secret of the webhooks. Without it, all webhooks are refused.
``GITHUB_APP_PRIVATE_KEY_FILE``
   The path of the private key of the app (PEM file), such as
   ``/app/data/github-app.pem`` in the volume of the data.
``GITHUB_APP_PRIVATE_KEY``
   The private key itself, instead of a file; ``\n`` stands for a line break.
``GITHUB_API``
   The API of GitHub. Default ``https://api.github.com``. Change it only for
   GitHub Enterprise Server.

.. _settings-data:

3. Data and secrets
===================

``DATA_DIR``
   The directory of the SQLite database and the generated secret key.
   ``/app/data`` in the image, the volume to back up; :file:`data/` in a
   checkout.
``SECRET_KEY``
   The key that signs the sessions and the tokens of the signing pages. If it
   is empty, a key is generated once into ``DATA_DIR`` and kept there. Keep it
   secret; changing it signs everybody out.
``DATABASE_URL``
   The database, such as ``postgres://user:password@db/agreements``. Default
   SQLite in ``DATA_DIR``.

.. _settings-email:

4. Email
========

The site writes to the administrators of installations when the app needs new
permissions, and about problems of their projects. Without ``EMAIL_HOST`` the
emails are written to the log.

``EMAIL_HOST``, ``EMAIL_PORT``
   The mail server and its port. Default port ``587``.
``EMAIL_HOST_USER``, ``EMAIL_HOST_PASSWORD``
   The account on the mail server.
``EMAIL_USE_SSL``, ``EMAIL_USE_TLS``
   The encryption: SSL for port ``465``, STARTTLS otherwise, by default.
``DEFAULT_FROM_EMAIL``
   The sender. Default ``agreements@<SITE_NAME>``.

.. _settings-people:

5. People
=========

``SITE_ADMINS``
   GitHub handles, comma separated, that may open the admin pages of Django.
   Default none.

.. _settings-look:

6. Name, look and links
=======================

``SITE_NAME``
   The name in the menu, the titles and the emails. Default ``ai.pycal.org``;
   ``make run`` uses the host of ``SITE_URL``.
``STATUS_CONTEXT``
   The start of the names of the checks on pull requests:
   ``<STATUS_CONTEXT>/<agreement>``. Default ``SITE_NAME``. Changing it
   creates new checks; update the required checks of the branch protection.
``FOOTER_LINKS``
   The extra links of the footer and the About page: ``Title=URL`` entries,
   comma separated, such as
   ``pycal.org=https://pycal.org,Blog=https://example.org/blog/``. Default
   ``pycal.org=https://pycal.org``; empty for none. A wrong entry stops the
   start with :class:`~ai_pycal.errors.configuration.InvalidFooterLink`.
``SOURCE_URL``
   The repository of the code, for the links of the footer and the About page.
   Default ``https://github.com/PyCalendar/ai.pycal.org``.
``DOCS_URL``
   The documentation, for the footer and the links of the errors and emails.
   Default ``https://docs.ai.pycal.org/``; ``make run``
   uses the local ``make livehtml`` server at ``http://localhost:8000/``. Set
   ``DOCS_PORT`` on both commands to use a different local port.
``COLOR_<NAME>``, ``COLOR_DARK_<NAME>``
   The colors of the light and the dark pages, such as ``COLOR_PRIMARY``. All
   names and defaults: :doc:`/how-to/brand`.
``EXTRA_CSS_URL``
   A style sheet loaded after that of the site. Default none.
``FAVICON``
   The icon of the site: an address such as ``https://pycal.org/favicon.png``,
   or the path of a PNG, ICO or SVG file such as ``/app/data/favicon.png``.
   Default the icon of pycal. See :doc:`/how-to/brand`.
``FAVICON_FILE``
   The older name of ``FAVICON``, still read if ``FAVICON`` is empty.

.. _settings-signing:

7. Signing
==========

``SIGN_MIN_SECONDS``
   Seconds between showing an agreement and signing it, at least. Default
   ``3``.
``SIGN_MAX_HOURS``
   Hours in which a shown agreement can be signed; after that the page must be
   loaded again. Default ``24``.

.. _settings-server:

8. The server
=============

These have good defaults in the image.

``PORT``
   The port in the container. Default ``5000``.
``WORKERS``, ``THREADS``
   The gunicorn processes and the threads of each. Default ``2`` and ``4``.
``LOG_LEVEL``
   ``DEBUG``, ``INFO``, ``WARNING`` or ``ERROR``. Default ``INFO``.
``DEBUG``
   ``true`` shows the details of failures in the pages. For development only,
   never on a public site. Default ``false``; ``make run`` sets ``1``.

.. _settings-build:

9. Build information
====================

The CI sets these, and ``make version`` (``docker/set_version.py``) writes
them into the image for the About page. They are not read by the running site.

``GITHUB_SHA``
   The commit; otherwise the commit of git.
``GITHUB_REF_TYPE``, ``GITHUB_REF_NAME``
   A tag ``v1.2.3`` makes the version ``1.2.3``.
``GITHUB_SERVER_URL``, ``GITHUB_REPOSITORY``, ``GITHUB_RUN_ID``
   The link to the CI build.
