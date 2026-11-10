=================
Create GitHub App
=================

Fill in this form and press **Create app on GitHub**. GitHub opens in a new
tab, where you review the name and confirm **Create GitHub App**. You must be
signed in to an account allowed to register the app for the chosen owner.

The form includes this project's required permissions and events. Callback,
installation and registration-return URLs are derived from your site URL.
For local development, keep ``http://localhost:5000`` and start ``make run``
before creating the app. For a deployed site, enter its public HTTPS address.

.. github-app-form::

Finish configuring the site
===========================

#. GitHub returns the new tab to your site with ``code`` and ``state`` in the
   URL. Copy that **whole return URL**. The homepage currently does not exchange
   the code automatically.
#. Return to this documentation tab and click **Save registration state**.
   Save the downloaded ``github-app-state.txt`` as
   ``data/github-app-state.txt`` in your checkout. Keep it unchanged and do not
   replace a state file from another registration that is still in progress.
#. Within one hour, follow :ref:`manifest-code-exchange` to exchange the code
   and save the app's private key and settings. That command checks your saved
   state against the return URL.
#. Copy the generated settings into ``.env`` and restart ``make run``. Use the
   same site address and app name here and in ``.env``. Then sign in and install
   the app from **Setup**.

If this tab is lost before you save the state, use a fresh registration attempt;
the code-exchange check requires the state of the attempt you submitted.
The form sends configuration to GitHub; it does not install the app or save
credentials to your checkout.

For the complete walkthrough, including the command-line alternative, see
:doc:`github-app-manifest`. For registration without a manifest, see
:doc:`github-app-manual`.

This form follows GitHub's `manifest registration examples
<https://docs.github.com/en/apps/sharing-github-apps/registering-a-github-app-from-a-manifest#examples>`_.
