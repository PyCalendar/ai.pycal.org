/* Assemble a GitHub manifest locally; credentials are exchanged on the operator's machine. */
(() => {
  "use strict";
  const form = document.getElementById("github-app-form");
  if (!form) return;

  const name = document.getElementById("app-name");
  const site = document.getElementById("app-site-url");
  const organization = document.getElementById("app-organization");
  const hidden = document.getElementById("app-manifest");
  const preview = document.getElementById("app-manifest-preview");
  const error = document.getElementById("app-form-error");
  const create = document.getElementById("app-create");
  const saveState = document.getElementById("app-save-state");
  const baseManifest = JSON.parse(hidden.value);
  let state;

  /** Validate the site address before deriving the URLs of the app, the webhook included. */
  function address(input) {
    let url;
    try {
      url = new URL(input.value.trim());
    } catch {
      throw new Error("Enter a complete site URL, including http:// or https://.");
    }
    if (!["http:", "https:"].includes(url.protocol) || url.username || url.password || url.hash) {
      throw new Error("Use an HTTP or HTTPS URL without login details or a fragment.");
    }
    if (url.search) {
      throw new Error("The site URL must not contain a query string.");
    }
    return url.href.replace(/\/+$/, "");
  }

  /** Keep the visible preview and the submitted JSON in sync with the form. */
  function update() {
    error.hidden = true;
    try {
      const base = address(site);
      const specification = JSON.parse(JSON.stringify(baseManifest));
      specification.name = name.value.trim();
      specification.url = base;
      specification.redirect_url = `${base}/`;
      specification.callback_urls = [`${base}/accounts/github/login/callback/`];
      specification.setup_url = `${base}/setup/installed/`;
      // the platform receives webhooks only at /github/webhook/ (ai_pycal/urls.py)
      specification.hook_attributes.url = `${base}/github/webhook/`;
      hidden.value = JSON.stringify(specification);
      preview.textContent = JSON.stringify(specification, null, 2);
      create.disabled = false;
      return true;
    } catch (problem) {
      error.textContent = problem.message;
      error.hidden = false;
      hidden.value = "";
      preview.textContent = "";
      create.disabled = true;
      return false;
    }
  }

  form.addEventListener("input", update);
  form.addEventListener("submit", (event) => {
    if (!update() || !name.value.trim() || !form.reportValidity()) {
      event.preventDefault();
      if (!name.value.trim()) {
        error.textContent = "Enter a GitHub App name.";
        error.hidden = false;
      }
      return;
    }
    // Generate the state only on submission, so later edits keep the same attempt.
    if (!state) {
      const bytes = new Uint8Array(32);
      crypto.getRandomValues(bytes);
      state = Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
    }
    const owner = organization.value.trim();
    const registration = owner
      ? `https://github.com/organizations/${encodeURIComponent(owner)}/settings/apps/new`
      : "https://github.com/settings/apps/new";
    form.action = `${registration}?state=${encodeURIComponent(state)}`;
    saveState.href = `data:text/plain;charset=utf-8,${state}`;
    saveState.hidden = false;
  });
  update();
})();
