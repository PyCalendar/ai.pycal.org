===================
Manual app creation
===================

Use this path to fill in GitHub's app registration form yourself, generate a
client secret and private key, and put the resulting values into the site.
This walkthrough uses ``http://localhost:5000`` and does not use the manifest
submission or conversion steps.
For the recommended submission form and the manifest CLI flow, return to
:doc:`github-app`.

1. Prepare the site and choose an app owner
===========================================

From the checkout:

.. code-block:: shell

   make dev
   test -f .env || cp .env.development.example .env
   mkdir -p data

Set ``SITE_URL=http://localhost:5000`` in ``.env``. Choose a distinct app name
of at most 34 characters and use it for ``SITE_NAME`` as well. Use a separate
app for development and for production.

For a deployed site, use its public HTTPS address everywhere below instead of
``http://localhost:5000``. The OAuth callback and installation setup must point
to that same site, and the webhook URL is always the site address plus
``/github/webhook/``. GitHub cannot deliver webhooks to localhost; see
:doc:`github-app-tunnel` for a public address of the local site with Tailscale
Funnel.

Open one of these registration pages while signed in to GitHub:

- Personal account: https://github.com/settings/apps/new
- Organization: ``https://github.com/organizations/ORGANIZATION/settings/apps/new``;
  replace ``ORGANIZATION`` with the organization login. Your account must have
  permission to register apps there.

2. Fill in the registration form
================================

Use these values for local development:

.. list-table:: Registration fields
   :header-rows: 1
   :widths: 35 65

   * - Field
     - Value
   * - GitHub App name
     - Your distinct app name; use the same name in ``SITE_NAME``.
   * - Homepage URL
     - ``http://localhost:5000``
   * - Callback URL
     - ``http://localhost:5000/accounts/github/login/callback/``
   * - Expire user authorization tokens
     - Keep selected; the site refreshes expiring tokens.
   * - Request user authorization (OAuth) during installation
     - Leave unchecked for this walkthrough. Sign in on the site before
       installing the app; the separate setup URL then remains available.
   * - Enable Device Flow
     - Leave unchecked.
   * - Setup URL
     - ``http://localhost:5000/setup/installed/``
   * - Redirect on update
     - Selected.
   * - Webhook Active
     - Selected.
   * - Webhook URL
     - Your public delivery URL; for a deployed site,
       ``https://<your site>/github/webhook/``.
   * - Webhook secret
     - A new random secret; save the same value as ``GITHUB_WEBHOOK_SECRET``.
   * - SSL verification
     - Enabled for the public HTTPS webhook delivery URL.
   * - Where can this GitHub App be installed?
     - Any account, so other projects can install the site's app.

Generate a webhook secret locally, for example:

.. code-block:: shell

   uv run python -c 'import secrets; print(secrets.token_urlsafe(32))'

The webhook secret is not a client secret. You generate the client secret in
step 4. GitHub hides the separate setup URL when OAuth during installation
is enabled; leaving that option off here lets GitHub return to
``/setup/installed/``. The site's **Sign in with GitHub** button still uses
the OAuth callback above.

3. Set permissions and events, then create the app
==================================================

Under **Repository permissions**, set:

- **Metadata**: Read-only (GitHub includes it automatically).
- **Contents**: Read-only.
- **Pull requests**: Read and write.
- **Commit statuses**: Read and write.

Under **Subscribe to events**, select **Pull request** and **Push**.
Leave other permissions and events at their defaults. The reasons for these
permissions are in :doc:`/reference/permissions`.

Press **Create GitHub App**. You now have an app registration; it still needs
credentials on the site and installation on the repositories.

4. Collect credentials and configure the site
=============================================

On the app's settings page:

#. Copy the numeric **App ID** to ``GITHUB_APP_ID``.
#. Copy the app's **slug** from its address, for example the last component of
   ``https://github.com/apps/your-app-slug``, to ``GITHUB_APP_SLUG``.
#. Copy **Client ID** to ``GITHUB_CLIENT_ID``. It differs from the numeric App ID.
#. Press **Generate a new client secret** and copy it to ``GITHUB_SECRET``.
#. Under **Private keys**, press **Generate a private key**. Save the downloaded
   PEM file as ``data/github-app.pem`` in the checkout. Use a new filename if
   that path already holds another app's key.

Complete these settings in ``.env``, replacing the example values:

.. code-block:: shell

   SITE_NAME=your-unique-development-app-name
   SITE_URL=http://localhost:5000
   GITHUB_APP_ID=123456
   GITHUB_APP_SLUG=your-app-slug
   GITHUB_CLIENT_ID=Iv23...
   GITHUB_SECRET=the-client-secret-from-github
   GITHUB_WEBHOOK_SECRET=the-webhook-secret-you-chose-in-step-2
   GITHUB_APP_PRIVATE_KEY_FILE=data/github-app.pem

Restrict access to the downloaded key:

.. code-block:: shell

   chmod 600 data/github-app.pem

For Docker, put the PEM file in the host's ``data`` directory, mount it at
``/app/data/github-app.pem`` and set ``GITHUB_APP_PRIVATE_KEY_FILE`` to that
container path. See :doc:`run-docker`. Keep the key and ``.env`` out of version
control. All environment settings are described in :doc:`/reference/settings`.

5. Start the site, sign in and install the app
==============================================

Run ``make run`` or restart it if it is already running. It reads ``.env`` and
supplies other missing local defaults. For Docker, restart the service with
its updated environment. There should be no ``ai_pycal.W001`` warning about
missing GitHub App settings.

Open http://localhost:5000/accounts/login/ and select **Sign in with GitHub**.
Then open **Setup**, press **Install the GitHub App** and select the repositories.
GitHub returns to the site's installation setup page.

Continue with :doc:`/tutorial/admin` to add the configuration file and activate
a repository. Open a test PR and check the app's recent webhook deliveries
on GitHub if no agreement checks appear.

These steps follow GitHub's `manual app registration guide
<https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/registering-a-github-app>`_.
