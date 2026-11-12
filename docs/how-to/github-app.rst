=====================
Set up the GitHub App
=====================

This guide is for the person running an instance of sign.pycal.org. Create one
GitHub App for the site, then configure the site with that app's credentials.
Maintainers using an already configured site can go straight to
:doc:`/tutorial/admin` to install its app on a repository.

Choose a setup flow
====================

**Register the app on the site.** It is the recommended way: start the site,
press **Register GitHub App** and confirm on GitHub; the site saves the
credentials in its volume. The other flows put the credentials into the
environment yourself, which takes precedence over the volume.

.. toctree::
   :maxdepth: 1
   :hidden:

   github-app-site
   create-github-app
   github-app-manifest
   github-app-manual
   github-app-tunnel

.. list-table:: Setup flows
   :header-rows: 1

   * - Flow
     - What you do
   * - :doc:`github-app-site` **(recommended)**
     - Press **Register GitHub App** on the running site, enter the setup code
       from its log and confirm on GitHub. The site saves the credentials in
       its volume and uses them at once.
   * - :doc:`create-github-app`
     - Fill in the documentation form, confirm on GitHub and exchange the
       return code. Permissions, events and callback URLs are filled in for you.
   * - :doc:`github-app-manifest`
     - Generate the manifest and registration form with commands, submit the
       local form and exchange the return code.
   * - :doc:`github-app-manual`
     - Fill in GitHub's registration settings, permissions and events yourself,
       then generate a client secret and private key.

Each of the other pages is a complete walkthrough, from preparing ``.env`` to signing in
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
