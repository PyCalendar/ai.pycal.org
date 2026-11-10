=====================
Create the GitHub App
=====================

This guide is for the person running an instance of ai.pycal.org. Create one
GitHub App for the site, then configure the site with that app's credentials.
Maintainers using an already configured site can go straight to
:doc:`/tutorial/admin` to install its app on a repository.

Choose a setup tutorial
=======================

.. toctree::
   :maxdepth: 1

   github-app-manifest
   create-github-app
   github-app-manual

- :doc:`github-app-manifest` walks through generating the manifest, submitting
  it in a browser, receiving GitHub's temporary code and exchanging that code
  for the app's credentials.
- :doc:`github-app-manual` walks through the GitHub registration form, choosing
  permissions, generating secrets and a private key, and configuring the site.

To submit a manifest directly from your browser, use :doc:`create-github-app`.

Both paths end with signing in and installing the app from the site's **Setup**
page. They cover the local ``http://localhost:5000`` setup and explain which
URLs and file paths change for a deployment.

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
