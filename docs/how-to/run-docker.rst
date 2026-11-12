========================
Run the site with Docker
========================

.. code-block:: shell

   git clone https://github.com/PyCalendar/sign.pycal.org.git
   cd sign.pycal.org
   cp .env.example .env    # then edit .env
   docker compose up -d

The site listens on port 5000. Put a proxy with TLS in front of it and set
``SITE_URL``, ``ALLOWED_HOSTS`` and ``CSRF_TRUSTED_ORIGINS`` to its address.

The SQLite database, the generated secret key and the private key of the
GitHub App are in ``./data``: keep it in your backups. Set ``DATABASE_URL`` for
PostgreSQL.

At each start the container migrates the database, sets the domain of the site
and checks the permissions of the installations (see :doc:`github-app`). A
minute after the start, and then every ``REPOSITORY_UPDATE_HOURS`` hours, it
updates every repository (``manage.py update_repositories``): webhooks lost
while the site was down are made up for, and pull requests merged meanwhile
show as merged. The
health check of the container reads ``/health/``.

Images
======

The CI pushes the image to ``ghcr.io/pycalendar/sign.pycal.org`` after all
checks passed: ``latest`` for each commit of ``main``; ``stable``, ``1.2.3``
and ``1.2`` for a tag ``v1.2.3``; for ``linux/amd64`` and ``linux/arm64``.
Before that, it starts the image until Docker sees it healthy
(``make docker-test``) and scans it with Trivy (``make docker-scan``), which
fails on critical vulnerabilities that have a fix. ``make docker-scan`` saves
the image to a file for Trivy, so Trivy needs no access to the Docker socket.

Deploy with Sencho
==================

The example deployment of the Python Calendaring Ecosystem is
https://sign.pycal.org, deployed this way. Its status:

.. image:: https://kuma.hosted.quelltext.eu/api/badge/48/status
   :alt: Status of sign.pycal.org
   :target: https://kuma.hosted.quelltext.eu/status/pycal

Sencho runs the stack of
:file:`docker-compose.yml` on the server, and the CI updates it after each
pushed image.

#. In Sencho, create the stack ``ai-pycal`` from :file:`docker-compose.yml`
   and put the ``.env`` of the site next to it, with ``SITE_URL``,
   ``ALLOWED_HOSTS`` and ``CSRF_TRUSTED_ORIGINS`` (:file:`.env.example` lists
   all settings).
#. Open the site and register its GitHub App with **Register GitHub App**
   (:doc:`github-app-site`); the setup code is in the log of the container.
   The credentials are saved in ``./data``.
#. The package ``ghcr.io/pycalendar/sign.pycal.org`` must be public, or Sencho
   must sign in to ghcr.io, to pull the image. Check its visibility in the
   package settings on GitHub after the first push.
#. Create an API token in Sencho. In the settings of the repository on
   GitHub, create the environment ``ai.pycal.org`` and add the token as its
   secret ``SENCHO_TOKEN``. A stack with another name is set with the
   repository variable ``SENCHO_STACK``.
#. Push to ``main``. The job *Deploy to Sencho* calls
   ``https://sencho.pycal.org/api/stacks/<stack>/update``; Sencho pulls the
   image and waits until the container is healthy. While the stack is deploying
   already, such as by hand, Sencho answers 409: the job waits 30 seconds and tries
   again, up to 10 times. Without ``SENCHO_TOKEN``,
   the job pushes the image and deploys nothing.

The health check sends the first host of ``ALLOWED_HOSTS``: with only
``sign.pycal.org`` allowed, Django would refuse a request for ``127.0.0.1``,
and Sencho would see the container as unhealthy. Sencho can also scan what it
deploys; that needs Trivy on the server itself.

Update
======

.. code-block:: shell

   docker compose pull
   docker compose up -d
