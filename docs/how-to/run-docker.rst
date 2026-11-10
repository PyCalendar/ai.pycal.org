========================
Run the site with Docker
========================

.. code-block:: shell

   git clone https://github.com/PyCalendar/ai.pycal.org.git
   cd ai.pycal.org
   cp .env.example .env    # then edit .env
   docker compose up -d

The site listens on port 5000. Put a proxy with TLS in front of it and set
``SITE_URL``, ``ALLOWED_HOSTS`` and ``CSRF_TRUSTED_ORIGINS`` to its address.

The SQLite database, the generated secret key and the private key of the
GitHub App are in ``./data``: keep it in your backups. Set ``DATABASE_URL`` for
PostgreSQL.

At each start the container migrates the database, sets the domain of the site
and checks the permissions of the installations (see :doc:`github-app`). The
health check of the container reads ``/health/``.

Update
======

.. code-block:: shell

   docker compose pull
   docker compose up -d
