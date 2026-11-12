===========================================
Test the GitHub App locally with Tailscale
===========================================

A site on ``http://localhost:5000`` can sign people in, because GitHub sends
the browser back to it. Webhooks are different: GitHub's servers deliver them,
and they cannot reach your computer. Without webhooks the site never hears of
pull requests, pushes or installations, so no checks or labels appear.

This guide makes the local site reachable on the internet with
`Tailscale Funnel <https://tailscale.com/kb/1223/funnel>`_, then registers a
development GitHub App for that address. Everything else stays local: the
database, ``.env`` and the private key.

.. note::

   ``tailscale serve`` only exposes the site to the devices of your tailnet.
   GitHub is not part of it, so use ``tailscale funnel``. Funnel makes the site
   public: anyone with the address can open it. Stop it when you are done.

1. Prepare Tailscale
====================

#. `Install Tailscale <https://tailscale.com/download>`_ on the computer that
   runs ``make run`` and sign in with ``tailscale up``.
#. In the `admin console <https://login.tailscale.com/admin>`_ of the tailnet,
   enable **MagicDNS** and **HTTPS certificates** (DNS page). Funnel needs
   both.
#. Allow Funnel for the computer. ``tailscale funnel`` shows a link to enable
   it when the tailnet policy does not allow it yet; the policy needs the
   ``funnel`` attribute for the computer.

2. Expose the site
==================

Start the tunnel to the port of ``make run`` in the background:

.. code-block:: shell

   tailscale funnel --bg 5000

The command prints the public address, such as
``https://laptop.tail1234.ts.net``. Tailscale ends HTTPS there and forwards
the requests to ``http://127.0.0.1:5000``. ``tailscale funnel status`` shows
the address again.

3. Configure the site for the address
=====================================

Put the address into ``.env``, without a slash at the end:

.. code-block:: shell

   SITE_URL=https://laptop.tail1234.ts.net
   SITE_NAME=your-unique-development-app-name

``make run`` and ``make app-manifest`` derive the rest from ``SITE_URL``:
``ALLOWED_HOSTS`` and ``CSRF_TRUSTED_ORIGINS`` include the address, and the
sign-in callback uses ``https``, also when the tunnel does not send
``X-Forwarded-Proto``. ``localhost`` stays allowed, so
``http://localhost:5000`` still opens the site, but sign in through the public
address: GitHub only returns to the registered callback.

Restart ``make run`` after changing ``.env`` and open the public address in
the browser. The start page should load.

4. Register the GitHub App
==========================

Open the public address and press **Register GitHub App**
(:doc:`github-app-site`): the app gets the public address, its webhook
included. ``make run`` asks for no setup code. Or follow one of the other
setup flows of :doc:`github-app` with the public address as the site address:

- :doc:`create-github-app`: enter the public address as **Site URL**. The
  webhook becomes ``https://laptop.tail1234.ts.net/github/webhook/``.
- :doc:`github-app-manifest`: ``make app-manifest`` already uses ``SITE_URL``.
- :doc:`github-app-manual`: use the public address instead of
  ``http://localhost:5000`` in every URL, including the webhook URL
  ``https://laptop.tail1234.ts.net/github/webhook/``.

Use a development app of its own, never the app of a deployed site: its
webhook URL points to your computer.

5. Test the whole flow
======================

#. Sign in on the public address and open **Setup**. Install the app on a test
   repository with :file:`.github/agreements.yml`, for example a fork of the
   example repository.
#. On GitHub, open the settings of the app, **Advanced**, **Recent
   Deliveries**. The ``installation`` event should have the response ``200``.
   **Redeliver** sends an event again after you fixed the site.
#. Open a pull request in the test repository. Its checks link to the public
   address; sign the agreements there and watch the checks and labels change.

The response of each delivery is JSON from the site; an error names its cause
and links to its documentation (:doc:`/reference/errors`). A ``401`` with
:class:`~ai_pycal.errors.webhooks.WebhookSignatureInvalid` means that the
webhook secret of the app and ``GITHUB_WEBHOOK_SECRET`` in ``.env`` differ. A delivery that never reaches
``make run`` means that the tunnel is down: check ``tailscale funnel status``.

6. Stop the tunnel
==================

.. code-block:: shell

   tailscale funnel reset

The site is private again. GitHub keeps the failed deliveries until you start
the tunnel again and redeliver them. The address of the computer stays the
same, so the app and ``.env`` keep working the next time.
