Within one hour of starting registration, run the next command. Paste the
return URL at its hidden prompt. It checks the saved state, exchanges the
code with GitHub and writes the private key and a settings fragment without
printing their contents:

.. code-block:: shell

   uv run python - <<'PY'
   import getpass
   import hmac
   import os
   from pathlib import Path
   from urllib.parse import parse_qs, quote, urlsplit

   import httpx

   for filename in ("data/github-app.pem", "data/github-app-settings.env"):
       if Path(filename).exists():
           raise SystemExit("Credential files already exist; choose fresh filenames before conversion.")
   returned = getpass.getpass("Paste the full manifest return URL: ")
   parameters = parse_qs(urlsplit(returned).query)
   expected = Path("data/github-app-state.txt").read_text()
   states = parameters.get("state", [])
   codes = parameters.get("code", [])
   if len(states) != 1 or not hmac.compare_digest(states[0], expected):
       raise SystemExit("The return state does not match this registration attempt.")
   if len(codes) != 1:
       raise SystemExit("The manifest return URL must contain one code.")
   response = httpx.post(
       "https://api.github.com/app-manifests/" + quote(codes[0], safe="") + "/conversions",
       headers={"Accept": "application/vnd.github+json"},
       timeout=20,
   )
   if response.status_code != 201:
       raise SystemExit("GitHub rejected the conversion; check the code and one-hour deadline.")
   credentials = response.json()
   pem = credentials["pem"]
   values = {
       "GITHUB_APP_ID": credentials["id"],
       "GITHUB_APP_SLUG": credentials["slug"],
       "GITHUB_CLIENT_ID": credentials["client_id"],
       "GITHUB_SECRET": credentials["client_secret"],
       "GITHUB_WEBHOOK_SECRET": credentials["webhook_secret"],
       "GITHUB_APP_PRIVATE_KEY_FILE": "data/github-app.pem",
   }
   os.umask(0o077)
   with Path("data/github-app.pem").open("x") as output:
       output.write(pem)
   with Path("data/github-app-settings.env").open("x") as output:
       output.write("".join(f"{key}={value}\n" for key, value in values.items()))
   print("Saved data/github-app.pem and data/github-app-settings.env.")
   PY

Open ``data/github-app-settings.env`` in your editor and copy its six settings
into ``.env``, replacing any existing values for those keys. These files
contain credentials; ``data/`` and ``.env`` are excluded from version control.
Keep the generated private key rather than generating another one on GitHub.

For Docker, mount the key as ``/app/data/github-app.pem`` and change
``GITHUB_APP_PRIVATE_KEY_FILE`` to that container path. The response fields
map directly to the six environment settings shown in the example;
``GITHUB_SECRET`` means the **client secret**, not the webhook secret or key.
