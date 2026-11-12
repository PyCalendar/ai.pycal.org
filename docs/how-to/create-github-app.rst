=====================================
App manifest with the submission form
=====================================

**Recommended default.** Use this form to register an app with the project's
required permissions and events. You need a GitHub account allowed to register
the app, a browser, and a checkout with ``uv`` installed to save credentials.
For the other setup flows, return to :doc:`github-app`.

1. Prepare the site
====================

From the checkout:

.. code-block:: shell

   make dev
   test -f .env || cp .env.development.example .env
   mkdir -p data

Set your app name and site address in ``.env``. Use the same values in the form:

.. code-block:: shell

   SITE_NAME=your-unique-development-app-name
   SITE_URL=http://localhost:5000

Choose a distinct app name of at most 34 characters. For a deployed site,
use its public HTTPS address; see :doc:`run-docker`. Start ``make run`` in
another terminal so the site can receive GitHub's registration return.

2. Submit the manifest
=======================

Fill in the form and press **Create app on GitHub**. GitHub opens in a new
tab, where you review the name and confirm **Create GitHub App**. Leave the
organization empty for your personal account, or enter its GitHub login.

All URLs of the app are derived from your site URL: callback, installation,
registration return and the webhook, which is always the site URL plus
``/github/webhook/``. GitHub cannot deliver webhooks to localhost; to test
them locally, make the site public with Tailscale Funnel as in
:doc:`github-app-tunnel` and enter that address as site URL.

.. github-app-form::

3. Save the return URL and registration state
=============================================

#. GitHub returns the new tab to your site with ``code`` and ``state`` in the
   URL. Copy that **whole return URL**. The homepage currently does not exchange
   the code automatically.
#. Return to this documentation tab and click **Save registration state**.
   Save the downloaded ``github-app-state.txt`` as
   ``data/github-app-state.txt`` in your checkout. Keep it unchanged and do not
   replace a state file from another registration that is still in progress.

If this tab is lost before you save the state, use a fresh registration attempt;
the code-exchange check requires the state of the attempt you submitted.
The form sends configuration to GitHub; it does not install the app or save
credentials to your checkout.

.. _manifest-form-code-exchange:

4. Exchange the code and configure credentials
==============================================

Keep the saved state file at ``data/github-app-state.txt``. The following
command checks it against the return URL before exchanging the code.

.. include:: ../_includes/github-app-manifest-exchange.rst

5. Restart, sign in and install the app
=======================================

.. include:: ../_includes/github-app-manifest-finish.rst

This form follows GitHub's `manifest registration examples
<https://docs.github.com/en/apps/sharing-github-apps/registering-a-github-app-from-a-manifest#examples>`_.
