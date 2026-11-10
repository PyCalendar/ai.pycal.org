=====================
App manifest CLI flow
=====================

Use this flow to generate a manifest and a registration form from the command
line, then exchange the return code for credentials. You need a GitHub account
allowed to register the app, a browser, and a checkout with ``uv`` installed.
For the recommended submission form or manual creation, return to
:doc:`github-app`.

The steps below configure a local site at ``http://localhost:5000``. The
manifest workflow consists of generating JSON, submitting it to GitHub in a
browser and exchanging GitHub's return code. **Printing the manifest alone
does not register or configure the app.**

1. Prepare the site and its URLs
================================

From the checkout:

.. code-block:: shell

   make dev
   test -f .env || cp .env.development.example .env
   mkdir -p data

Edit ``.env`` to choose a distinct app name and the address of this site:

.. code-block:: shell

   SITE_NAME=your-unique-development-app-name
   SITE_URL=http://localhost:5000

Choose an app name of at most 34 characters that is available on GitHub; you
can also adjust it on GitHub's confirmation page. ``make app-manifest`` and
``make run`` both read these values. Without an explicit ``SITE_URL``, they
use ``http://localhost:5000``. If you use ``PORT=5001``, use that port in both
commands and in an explicitly configured ``SITE_URL``.

For a deployed site, set ``SITE_URL`` to its public HTTPS address before
creating the manifest. See :doc:`run-docker` for deployment. GitHub cannot
deliver webhooks to localhost: for local testing, arrange a webhook forwarding
URL and use it for the app's webhook URL. The browser-facing redirect and
OAuth callback can remain on localhost. The form-creation step below lets you
set a separate forwarded webhook URL.

2. Generate the manifest
========================

.. code-block:: shell

   make app-manifest > data/github-app-manifest.json

The file contains the required permissions and events. Its default URLs are:

.. list-table:: Local URLs
   :header-rows: 1

   * - Purpose
     - URL
   * - Homepage and manifest registration return
     - ``http://localhost:5000/``
   * - OAuth sign-in callback
     - ``http://localhost:5000/accounts/github/login/callback/``
   * - Installation setup
     - ``http://localhost:5000/setup/installed/``
   * - Webhook delivery
     - ``http://localhost:5000/github/webhook/``

For a running container, generate the deployment JSON with
``docker compose exec ai-pycal python manage.py app_manifest`` and save its
output to ``data/github-app-manifest.json`` in the checkout used for the next
step. The running container must already have the intended ``SITE_URL``.

3. Submit the manifest in your browser
======================================

Create a local registration form with the following command. Change
``organization`` to your organization's GitHub login to register the app
there, or leave it empty for your personal account. If you use a forwarding
service for local webhooks, put its public delivery URL in ``webhook_url``.

.. code-block:: shell

   uv run python - <<'PY'
   import html
   import json
   import secrets
   from pathlib import Path
   from urllib.parse import quote, urlencode

   organization = ""
   webhook_url = ""
   manifest = json.loads(Path("data/github-app-manifest.json").read_text())
   for filename in ("data/github-app-state.txt", "data/github-app-register.html"):
       if Path(filename).exists():
           raise SystemExit("Registration files already exist; choose fresh filenames.")
   if webhook_url:
       manifest["hook_attributes"]["url"] = webhook_url
   registration_url = (
       "https://github.com/organizations/" + quote(organization, safe="") + "/settings/apps/new"
       if organization else "https://github.com/settings/apps/new"
   )
   state = secrets.token_urlsafe(32)
   action = registration_url + "?" + urlencode({"state": state})
   form = (
       '<!doctype html><meta charset="utf-8"><title>Register the GitHub App</title>'
       '<h1>Register the GitHub App</h1>'
       f'<form method="post" action="{html.escape(action, quote=True)}">'
       f'<input type="hidden" name="manifest" value="{html.escape(json.dumps(manifest), quote=True)}">'
       '<button type="submit">Continue on GitHub</button></form>'
   )
   with Path("data/github-app-state.txt").open("x") as output:
       output.write(state)
   with Path("data/github-app-register.html").open("x") as output:
       output.write(form)
   print("Open http://localhost:5002/github-app-register.html after starting the form server.")
   PY

The example creates new files and refuses to replace an existing registration
form or state file. If you restart registration, choose fresh filenames
consistently in both Python examples or remove only the files from your
abandoned attempt.

In one terminal start the site; it can display its homepage before the app
credentials are configured:

.. code-block:: shell

   make run

In another terminal, serve the registration form on a separate local port:

.. code-block:: shell

   uv run python -m http.server 5002 --bind 127.0.0.1 --directory data

Open http://localhost:5002/github-app-register.html and press **Continue on
GitHub**. Review the app name and account, then press GitHub's **Create GitHub
App** button. This submits the JSON as a ``manifest`` form field; there is no
JSON upload box on GitHub's ordinary registration form.

.. _manifest-code-exchange:

4. Exchange the return code and save the credentials
====================================================

GitHub returns your browser to a URL such as:

.. code-block:: text

   http://localhost:5000/?code=RETURN_CODE&state=RETURN_STATE

The homepage currently does not exchange this code automatically. Copy the
**whole return URL** from your browser's address bar. This is the manifest
registration return to ``/``, not the OAuth callback under ``/accounts/``.
Stop the form server with Ctrl-C before saving credentials into ``data``.
Leave the site running until you have copied the return URL.

.. include:: ../_includes/github-app-manifest-exchange.rst

5. Restart, sign in and install the app
=======================================

.. include:: ../_includes/github-app-manifest-finish.rst

The registration and conversion steps follow GitHub's `manifest workflow
<https://docs.github.com/en/apps/sharing-github-apps/registering-a-github-app-from-a-manifest>`_
and `manifest conversion endpoint
<https://docs.github.com/en/rest/apps/apps#create-a-github-app-from-a-manifest>`_.
