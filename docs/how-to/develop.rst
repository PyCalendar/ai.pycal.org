========
Develop
========

Set up the development environment and run the site:

.. code-block:: shell

   make dev        # Python, the packages, the git hooks, the recording of AI prompts and the database
   make run        # the site on http://localhost:5000

In a second terminal, run ``make livehtml`` to serve this documentation at
``http://localhost:8000/``. ``make run`` points documentation, changelog,
error descriptions and help links to that local server unless ``DOCS_URL`` is
already set in the environment or ``.env``. Configured values take precedence.

Both commands accept ``DOCS_PORT`` if port 8000 is already in use:

.. code-block:: shell

   make livehtml DOCS_PORT=8001
   make run DOCS_PORT=8001

``make dev`` needs `uv <https://docs.astral.sh/uv/>`_ and can be run again at
any time, for example after the packages changed. ``make run`` reads the
settings of :file:`.env` if it exists. Use the local test configuration below
to start.
After loading it, missing or empty development settings get these defaults:
``DEBUG=1``, ``SITE_URL=http://localhost:5000``, ``SITE_NAME=localhost``,
``ALLOWED_HOSTS=localhost,127.0.0.1,[::1]``,
``CSRF_TRUSTED_ORIGINS=http://localhost:5000`` and
``DOCS_URL=http://localhost:8000/``. An explicit ``SITE_URL`` supplies the
default site name, allowed host and CSRF origin. Explicit values, including
``DEBUG=0``, are preserved. The existing secret-key generation and SQLite
database defaults continue to apply. GitHub credentials come from your GitHub
App configuration.
Without a GitHub App, the pages can be seen but signing in shows
:class:`~ai_pycal.errors.github.SignInNotConfigured`. Another port:
``make run PORT=5001``.

.. _development-configuration:

Configure the site
==================

Keep the local test settings in a file named ``.env`` at the root of the
checkout. Start with the development example, preserving an existing file:

.. code-block:: shell

   test -f .env || cp .env.development.example .env

The example contains the settings to fill in:

.. literalinclude:: ../../.env.development.example
   :language: shell

Set the six ``GITHUB_*`` values from your development GitHub App, and save its
private key at the path named by ``GITHUB_APP_PRIVATE_KEY_FILE``.
``GITHUB_SECRET`` is the client secret; ``GITHUB_WEBHOOK_SECRET`` is the
separate webhook secret. Choose a unique ``SITE_NAME`` before creating the
app. Follow :doc:`github-app-manifest` or :doc:`github-app-manual` to obtain
the credentials.

Run ``make run`` after saving the file, or stop and restart it if it is
already running. Both ``make run`` and ``make app-manifest`` load ``.env``
automatically; no shell ``export`` commands are needed. The file is excluded
from version control. Leave ``SITE_URL`` and ``DOCS_URL`` empty to use the
local defaults and any ``PORT`` / ``DOCS_PORT`` overrides.
The general :file:`.env.example` lists additional settings for deployments.

Generate the development GitHub App manifest with the same defaults:

.. code-block:: shell

   make app-manifest

Its site, redirect, OAuth callback, setup and webhook URLs use
``http://localhost:5000`` by default. Use the same ``PORT`` value for
``make run`` and ``make app-manifest`` when choosing another port. Set
``SITE_URL`` explicitly for a tunnel or another address. These defaults apply
only to development commands; production settings keep their existing defaults.

.. code-block:: shell

   make test       # the tests with coverage
   make lint       # ruff
   make docs       # this documentation
   make reuse      # the licenses

The tests never use the network: :file:`tests/fakes/github.py` is a fake GitHub
that answers the requests of the site.
The test fixture in ``tests/data/agreements.yml`` makes both agreements
mandatory to exercise signing checks. The example repository keeps the AI
policy optional; a regression check verifies that this is their only
configuration difference and that the agreement texts match.

The rules for the code, such as one class per module and one error class per
cause, are in :file:`AGENTS.md`.

Run the site with a GitHub App
==============================

Create a second GitHub App for development using either
:doc:`github-app-manifest` or :doc:`github-app-manual`, with
``http://localhost:5000`` as address, and put its settings into :file:`.env`. GitHub can not send webhooks to
``localhost``: forward them with `smee.io <https://smee.io>`_ or the ``gh
webhook forward`` extension of the GitHub CLI.
