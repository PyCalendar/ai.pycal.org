=====================
Set up the GitHub App
=====================

This guide is for the person running an instance of ai.pycal.org. Create one
GitHub App for the site, then configure the site with that app's credentials.
Maintainers using an already configured site can go straight to
:doc:`/tutorial/admin` to install its app on a repository.

Choose a setup flow
====================

**Start with the submission form.** It is the recommended default: enter your
site details and submit the manifest directly from the documentation.
Choose the CLI flow if you prefer to generate the registration form locally,
or create the app manually if you want to fill in GitHub's settings yourself.

.. toctree::
   :maxdepth: 1
   :hidden:

   create-github-app
   github-app-manifest
   github-app-manual
   github-app-tunnel

.. list-table:: Setup flows
   :header-rows: 1

   * - Flow
     - What you do
   * - :doc:`create-github-app` **(recommended default)**
     - Fill in the documentation form, confirm on GitHub and exchange the
       return code. Permissions, events and callback URLs are filled in for you.
   * - :doc:`github-app-manifest`
     - Generate the manifest and registration form with commands, submit the
       local form and exchange the return code.
   * - :doc:`github-app-manual`
     - Fill in GitHub's registration settings, permissions and events yourself,
       then generate a client secret and private key.

Each page is a complete walkthrough, from preparing ``.env`` to signing in
and installing the app from the site's **Setup** page. All three cover the
local ``http://localhost:5000`` setup and explain the changes for deployment.

Test locally with webhooks
==========================

GitHub cannot deliver webhooks to ``localhost``. To test pull requests,
checks and labels on your computer, make the local site public with Tailscale
Funnel and register the app for that address: see :doc:`github-app-tunnel`.

New permissions
===============

When a new version of the site needs more permissions, update the permissions
of the app on GitHub. GitHub asks the owners of each installation to accept
them. The site also writes to the administrators of each installation:
``manage.py check_permissions`` runs at each start and once a day in the
container. The required permissions and events are listed in
:doc:`/reference/permissions`.

Expiring user tokens
====================

Keep **User-to-server token expiration** enabled in the GitHub App's optional
features. When an administrator opens a setup page, the site automatically
renews a stored user access token if it expires within sixty seconds. It saves
the replacement access token, refresh token and expiry together. Requests for
the same stored token are serialized during renewal because GitHub invalidates
each refresh token after use.

The client ID and client secret used to sign in are also used for renewal.
Tokens issued without an expiry continue to work without renewal. If an old
sign in has no refresh token, or GitHub rejects renewal because authorization
was revoked or the refresh token expired, the person must sign out and sign
in again. Temporary GitHub failures leave the stored credentials intact so
renewal can be retried.

See GitHub's `refreshing user access tokens
<https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/refreshing-user-access-tokens>`_
for the token lifetimes and rotation rules.
