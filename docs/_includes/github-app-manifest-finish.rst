Stop the development server and run ``make run`` again so it reads the new
credentials. For Docker, restart the service with its updated environment.
There should be no ``ai_pycal.W001`` warning about missing GitHub App settings.

Open http://localhost:5000/accounts/login/, sign in with GitHub, open **Setup**
and press **Install the GitHub App**. Select the repositories to include.
Registration creates the app; installation grants it access to repositories.
Continue with :doc:`/tutorial/admin` to add ``.github/agreements.yml`` and
activate a repository. Open a test PR and inspect the app's recent webhook
deliveries on GitHub if it is not checked.
