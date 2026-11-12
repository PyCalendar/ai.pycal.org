Register the GitHub App on the running site: **Register GitHub App** on the
sign-in and setup pages, protected by a setup code from the log, saves the
credentials into the volume (``DATA_DIR/.env`` and the key file), which the site
reads at every start; settings of the environment take precedence. A local
address is registered without a webhook, and the page says so.
