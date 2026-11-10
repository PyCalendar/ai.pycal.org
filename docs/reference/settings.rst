========
Settings
========

The site is configured with environment variables, such as in ``.env``.
:file:`.env.example` contains all of them with comments.
For a local test setup, copy :file:`.env.development.example` to ``.env``,
fill in the GitHub App credentials and restart ``make run``. See
:ref:`the development configuration <development-configuration>`.

The site
========

``SITE_NAME``
   The name in the menu and the titles. Default ``ai.pycal.org``.
``SITE_URL``
   The address of the site, for the links of the checks and emails. Default
   ``https://ai.pycal.org``.
``ALLOWED_HOSTS``, ``CSRF_TRUSTED_ORIGINS``
   The host names of the site, and its address with ``https://``, comma
   separated.
``SITE_ADMINS``
   GitHub handles, comma separated, that can open the admin pages of Django.
``DEBUG``
   ``true`` for development only.
``SECRET_KEY``
   Generated into ``DATA_DIR`` if empty.
``DATA_DIR``
   The directory of the database and the secret key. ``/app/data`` in the
   image.
``DATABASE_URL``
   Such as ``postgres://user:password@db/agreements``; SQLite in ``DATA_DIR`` by
   default.
``SOURCE_URL``, ``DOCS_URL``
   The code and the documentation, for the links of the pages. ``DOCS_URL``
   also controls error descriptions and help links. ``make run`` uses the
   local ``make livehtml`` server at ``http://localhost:8000/`` when unset;
   set ``DOCS_PORT`` on both commands to use a different local port.

The GitHub App
==============

See :doc:`/how-to/github-app`.

``GITHUB_APP_ID``, ``GITHUB_APP_SLUG``
   The id and the name in the address of the app.
``GITHUB_APP_PRIVATE_KEY`` or ``GITHUB_APP_PRIVATE_KEY_FILE``
   The private key of the app, or the path of its PEM file.
``GITHUB_CLIENT_ID``, ``GITHUB_SECRET``
   The client id and a client secret of the app, for signing in.
``GITHUB_WEBHOOK_SECRET``
   The secret of the webhooks. Without it, all webhooks are refused.
``GITHUB_API``
   The API of GitHub. Default ``https://api.github.com``.
``STATUS_CONTEXT``
   The start of the names of the checks: ``<STATUS_CONTEXT>/<agreement>``.
   Default ``SITE_NAME``.

Signing
========

``SIGN_MIN_SECONDS``
   Seconds between showing an agreement and signing it, at least. Default
   ``3``.
``SIGN_MAX_HOURS``
   Hours in which a shown agreement can be signed. Default ``24``.

Colors and icon
===============

``COLOR_<NAME>``, ``COLOR_DARK_<NAME>``, ``EXTRA_CSS_URL``, ``FAVICON_FILE``:
see :doc:`/how-to/brand`.

Email
=====

``EMAIL_HOST``, ``EMAIL_PORT``, ``EMAIL_HOST_USER``, ``EMAIL_HOST_PASSWORD``, ``EMAIL_USE_SSL``, ``EMAIL_USE_TLS``, ``DEFAULT_FROM_EMAIL``
   The mail server for the emails about permissions. Without ``EMAIL_HOST`` the
   emails are written to the log.

The server
==========

``PORT``, ``WORKERS``, ``THREADS``
   The port of the container and the gunicorn processes and threads.
``LOG_LEVEL``
   Default ``INFO``.
