===================================
Register the GitHub App on the site
===================================

**Recommended.** A running site registers its own GitHub App: it builds the
manifest with its address, permissions and events, GitHub creates the app, and
the site saves the credentials in its volume. You need a GitHub account allowed
to create apps for the owner you choose, and the setup code of the site.

1. Start the site
=================

Start the site without any ``GITHUB_...`` settings (empty ones, as in
:file:`.env.example`, count as unset; ``GITHUB_APP_PRIVATE_KEY_FILE`` may name
the file for the key), for example with
``docker compose up -d`` (:doc:`run-docker`) or ``make run``
(:doc:`develop`). Set ``SITE_URL`` to the address that people and GitHub use;
the app is registered for it.

While the site has no app, it writes a line like this into its log at every
start:

.. code-block:: text

   This site has no GitHub App. Register it on https://ai.example.org/setup/github-app/ with the setup code 3f9a-0c41-77d2

The code is also in ``DATA_DIR/github-app-setup-code``, and this command shows
it:

.. code-block:: shell

   docker compose exec ai-pycal python manage.py github_app_setup_code

If the environment sets a ``GITHUB_...`` setting of an app, the site offers no
registration: the sign-in, setup and registration pages, the log and the
command name the settings that are set, because they would take precedence
over the registered app. The same holds for an existing file of the private
key, which the site never overwrites. Set all settings of that app, or remove
them and restart the site.

Only who can read the log or the volume can register the app: without the code,
anybody who finds a new site could register their own app for it. With
``DEBUG`` on, as with ``make run``, the page asks for no code.

2. Register the app
===================

#. Open the site. Without an app, **Sign in** and **Setup** show the button
   **Register GitHub App**; it leads to ``/setup/github-app/``.
#. Enter the name of the app (at most 34 characters, unique on GitHub), the
   organization that will own it, or nothing for your own account, and the
   setup code. Press **Register GitHub App**.
#. The site shows the manifest. Press **Continue to GitHub**. GitHub shows the
   form of a new app, filled in. Press **Create GitHub App**.
#. GitHub returns to ``/setup/github-app/registered/``. The site exchanges the
   code of GitHub for the credentials of the app, saves them and uses them at
   once. The page links to the next steps: sign in, install the app on a
   repository and add the repository on **Setup**.

The webhook of the app is always the address of the site plus
``/github/webhook/``.

Local addresses
---------------

GitHub cannot reach ``http://localhost:5000`` or other local addresses. The
page says so before you register: signing in works, because GitHub sends the
browser back to the site, but webhooks cannot be delivered, so the app is
registered without a webhook and pull requests are not checked. To test
everything, give the site a public address first, as
:doc:`github-app-tunnel` shows, and set ``SITE_URL`` to it before you register.

Errors
------

Errors that GitHub shows, such as a name that is taken, appear on GitHub's
form: go back to the site and start again. Errors of the site have a page with
their name, what to do and **Details to copy**: the error, the HTTP status, the
answer of GitHub, the page, the time and the version. Copy them into a bug
report. The errors are listed in :doc:`/reference/errors`.

A registration belongs to the browser that started it, and the code that
GitHub returns is valid for an hour and once. If the exchange fails after
GitHub created the app, delete the app in the settings of the GitHub account
and register again.

3. Where the credentials are
============================

The site writes two files into ``DATA_DIR`` (``/app/data`` in the container),
readable only by the site:

``DATA_DIR/.env``
   ``GITHUB_APP_ID``, ``GITHUB_APP_SLUG``, ``GITHUB_CLIENT_ID``,
   ``GITHUB_SECRET``, ``GITHUB_WEBHOOK_SECRET`` and
   ``GITHUB_APP_PRIVATE_KEY_FILE``.
``DATA_DIR/github-app.pem``
   The private key of the app; or the file of ``GITHUB_APP_PRIVATE_KEY_FILE``
   if the environment sets it, as :file:`.env.example` does with
   ``/app/data/github-app.pem``. The registration never overwrites a file: if
   one exists there, it stops with
   :class:`~ai_pycal.errors.registration.PrivateKeyFileExists`.

The site reads ``DATA_DIR/.env`` at every start. A variable of the
environment, such as in the ``.env`` of Docker Compose, takes precedence; an
empty one counts as unset. Back up the volume and keep both files secret.

.. _oauth-app:

Sign people in without acting on their behalf
=============================================

When people sign in with a GitHub App, GitHub asks them to let it act on their
behalf, although the site only reads who they are. An OAuth app without scopes
signs them in with read access to their public information only; the GitHub
App keeps writing labels and checks with its own token, and reads whether a
person has the role *admin* or *maintain* of a repository by itself.

GitHub has no manifest for OAuth apps, so it is created by hand:

#. On GitHub, open *Settings → Developer settings → OAuth apps → New OAuth
   app*, of your account or of the organization.
#. Homepage URL: the address of the site. Authorization callback URL: the
   address of the site plus ``/accounts/github/login/callback/``.
#. Register it and generate a client secret.
#. On the page **Setup**, administrators of the site (``SITE_ADMINS``) follow
   **Set up the OAuth app** and enter the client ID and the secret. They are
   kept in ``DATA_DIR/.env``. Or set ``GITHUB_OAUTH_CLIENT_ID`` and
   ``GITHUB_OAUTH_SECRET`` in the environment.

One app per site
================

A site has one GitHub App. When the site has one, from the environment or from
the volume, ``/setup/github-app/`` shows where it comes from and registers no
other. To change the app, remove its ``GITHUB_...`` settings from the
environment and ``DATA_DIR/.env``, delete ``DATA_DIR/github-app.pem``, restart
the site and register again; delete the old app on GitHub.
