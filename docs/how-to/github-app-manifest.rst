=================================================
Configure the site with the app manifest workflow
=================================================

Use this path to let GitHub create the app, private key, client secret and
webhook secret from the site's manifest. You need a GitHub account allowed to
register the app, a browser, and a checkout with ``uv`` installed.

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

The easiest option is :doc:`create-github-app`: fill in the app name and site
URL, optionally choose an organization and forwarded webhook URL, and press
**Create app on GitHub**. After confirming on GitHub, return to that page to
save its registration state file and continue with :ref:`manifest-code-exchange`.
This replaces the form-generation and form-server commands below.

Command-line alternative
------------------------

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

Within one hour of starting registration, run the next command. Paste the
return URL at its hidden prompt. It checks the saved state, exchanges the
code with GitHub and writes the private key and a settings fragment without
printing their contents:

.. code-block:: shell

   uv run python - <<'PY'
   import getpass
   import hmac
   import os
   from pathlib import Path
   from urllib.parse import parse_qs, quote, urlsplit

   import httpx

   for filename in ("data/github-app.pem", "data/github-app-settings.env"):
       if Path(filename).exists():
           raise SystemExit("Credential files already exist; choose fresh filenames before conversion.")
   returned = getpass.getpass("Paste the full manifest return URL: ")
   parameters = parse_qs(urlsplit(returned).query)
   expected = Path("data/github-app-state.txt").read_text()
   states = parameters.get("state", [])
   codes = parameters.get("code", [])
   if len(states) != 1 or not hmac.compare_digest(states[0], expected):
       raise SystemExit("The return state does not match this registration attempt.")
   if len(codes) != 1:
       raise SystemExit("The manifest return URL must contain one code.")
   response = httpx.post(
       "https://api.github.com/app-manifests/" + quote(codes[0], safe="") + "/conversions",
       headers={"Accept": "application/vnd.github+json"},
       timeout=20,
   )
   if response.status_code != 201:
       raise SystemExit("GitHub rejected the conversion; check the code and one-hour deadline.")
   credentials = response.json()
   pem = credentials["pem"]
   values = {
       "GITHUB_APP_ID": credentials["id"],
       "GITHUB_APP_SLUG": credentials["slug"],
       "GITHUB_CLIENT_ID": credentials["client_id"],
       "GITHUB_SECRET": credentials["client_secret"],
       "GITHUB_WEBHOOK_SECRET": credentials["webhook_secret"],
       "GITHUB_APP_PRIVATE_KEY_FILE": "data/github-app.pem",
   }
   os.umask(0o077)
   with Path("data/github-app.pem").open("x") as output:
       output.write(pem)
   with Path("data/github-app-settings.env").open("x") as output:
       output.write("".join(f"{key}={value}\n" for key, value in values.items()))
   print("Saved data/github-app.pem and data/github-app-settings.env.")
   PY

Open ``data/github-app-settings.env`` in your editor and copy its six settings
into ``.env``, replacing any existing values for those keys. These files
contain credentials; ``data/`` and ``.env`` are excluded from version control.
Keep the generated private key rather than generating another one on GitHub.

For Docker, mount the key as ``/app/data/github-app.pem`` and change
``GITHUB_APP_PRIVATE_KEY_FILE`` to that container path. The response fields
map directly to the six environment settings shown in the example;
``GITHUB_SECRET`` means the **client secret**, not the webhook secret or key.

5. Restart, sign in and install the app
=======================================

Stop the development server and run ``make run`` again so it reads the new
credentials. For Docker, restart the service with its updated environment.
There should be no ``ai_pycal.W001`` warning about missing GitHub App settings.

Open http://localhost:5000/accounts/login/, sign in with GitHub, open **Setup**
and press **Install the GitHub App**. Select the repositories to include.
Registration creates the app; installation grants it access to repositories.
Continue with :doc:`/tutorial/admin` to add ``.github/agreements.yml`` and
activate a repository. Open a test PR and inspect the app's recent webhook
deliveries on GitHub if it is not checked.

The registration and conversion steps follow GitHub's `manifest workflow
<https://docs.github.com/en/apps/sharing-github-apps/registering-a-github-app-from-a-manifest>`_
and `manifest conversion endpoint
<https://docs.github.com/en/rest/apps/apps#create-a-github-app-from-a-manifest>`_.
