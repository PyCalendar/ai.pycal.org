/* Run the real docs script against a small DOM with no network or GitHub submission. */
const assert = require("node:assert/strict");
const { webcrypto } = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "../../docs/_static/github-app-form.js"), "utf8");
const html = process.env.GITHUB_FORM_HTML;
const unescape = (value) => value.replace(/&quot;/g, '"').replace(/&#x27;/g, "'")
  .replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&amp;/g, "&");

function browser() {
  const elements = {};
  for (const match of html.matchAll(/<(?:input|form|button|a|pre|p)\b([^>]*\bid="([^"]+)"[^>]*)>/g)) {
    const attributes = Object.fromEntries(Array.from(match[1].matchAll(/([\w-]+)="([^"]*)"/g),
      (attribute) => [attribute[1], unescape(attribute[2])]));
    const listeners = {};
    elements[match[2]] = {
      value: attributes.value || "", hidden: /\bhidden\b/.test(match[1]),
      disabled: /\bdisabled\b/.test(match[1]), textContent: "", attributes,
      addEventListener: (name, handler) => { listeners[name] = handler; },
      reportValidity: () => Object.values(elements).every((element) => {
        const { attributes, value } = element;
        return (!attributes.maxlength || value.length <= Number(attributes.maxlength)) &&
          (!attributes.pattern || !value || new RegExp(`^(?:${attributes.pattern})$`).test(value));
      }),
      fire(name) {
        const event = { prevented: false, preventDefault() { this.prevented = true; } };
        listeners[name](event);
        return event;
      },
    };
  }
  vm.runInNewContext(source, {
    document: { getElementById: (id) => elements[id] },
    crypto: webcrypto, URL, Uint8Array, encodeURIComponent,
  });
  return {
    elements,
    form: elements["github-app-form"],
    payload: () => JSON.parse(elements["app-manifest"].value),
    set(id, value) {
      elements[id].value = value;
      elements["github-app-form"].fire("input");
    },
  };
}

test("local defaults keep the application permissions and derived URLs", () => {
  const page = browser();
  const initial = JSON.parse(unescape(html.match(/id="app-manifest"[^>]*value="([^"]+)"/)[1]));
  assert.deepEqual(page.payload(), initial);
  assert.equal(page.payload().url, "http://localhost:5000");
  assert.equal(page.payload().callback_urls[0], "http://localhost:5000/accounts/github/login/callback/");
  assert.equal(page.payload().setup_url, "http://localhost:5000/setup/installed/");
  assert.equal(page.elements["app-create"].disabled, false);
});

test("personal registration sends JSON and offers matching random state", () => {
  const page = browser();
  page.set("app-name", 'My app "<&>');
  assert.equal(page.form.fire("submit").prevented, false);
  assert.equal(page.payload().name, 'My app "<&>');
  const action = new URL(page.form.action);
  assert.equal(action.origin, "https://github.com");
  assert.equal(action.pathname, "/settings/apps/new");
  const state = action.searchParams.get("state");
  assert.match(state, /^[0-9a-f]{64}$/);
  assert.equal(page.elements["app-save-state"].href, `data:text/plain;charset=utf-8,${state}`);
  assert.equal(page.elements["app-save-state"].hidden, false);
  assert.deepEqual(JSON.parse(page.elements["app-manifest-preview"].textContent), page.payload());
  page.set("app-name", "Revised name");
  page.form.fire("submit");
  assert.equal(new URL(page.form.action).searchParams.get("state"), state);
  const other = browser();
  other.set("app-name", "Another app");
  other.form.fire("submit");
  assert.notEqual(new URL(other.form.action).searchParams.get("state"), state);
});

test("organization and deployed site prefix are used; the webhook follows the site", () => {
  const page = browser();
  page.set("app-name", "Organization app");
  page.set("app-organization", "PyCalendar");
  page.set("app-site-url", "https://ai.example.org/service/");
  assert.equal(page.form.fire("submit").prevented, false);
  assert.equal(new URL(page.form.action).pathname, "/organizations/PyCalendar/settings/apps/new");
  assert.equal(page.payload().url, "https://ai.example.org/service");
  assert.equal(page.payload().redirect_url, "https://ai.example.org/service/");
  assert.equal(page.payload().callback_urls[0], "https://ai.example.org/service/accounts/github/login/callback/");
  assert.equal(page.payload().setup_url, "https://ai.example.org/service/setup/installed/");
  assert.equal(page.payload().hook_attributes.url, "https://ai.example.org/service/github/webhook/");
});

for (const url of ["javascript:alert(1)", "broken", "https://name:secret@example.org", "https://example.org/#part", "https://example.org/?query=1"]) {
  test(`invalid site address is rejected: ${url}`, () => {
    const page = browser();
    page.set("app-name", "Test app");
    page.set("app-site-url", url);
    assert.equal(page.elements["app-create"].disabled, true);
    assert.equal(page.elements["app-form-error"].hidden, false);
    assert.equal(page.form.fire("submit").prevented, true);
    assert.equal(page.elements["app-manifest"].value, "");
    page.set("app-site-url", "http://localhost:5000");
    assert.equal(page.elements["app-create"].disabled, false);
    assert.equal(page.elements["app-form-error"].hidden, true);
  });
}

test("the form has no field for the webhook", () => {
  const page = browser();
  assert.equal(page.elements["app-webhook-url"], undefined);
});

test("blank names, overlong names and invalid organization logins are rejected", () => {
  const page = browser();
  page.set("app-name", "   ");
  assert.equal(page.form.fire("submit").prevented, true);
  assert.equal(page.elements["app-form-error"].textContent, "Enter a GitHub App name.");
  page.set("app-name", "x".repeat(35));
  assert.equal(page.form.fire("submit").prevented, true);
  page.set("app-name", "Test app");
  page.set("app-organization", "bad/owner");
  assert.equal(page.form.fire("submit").prevented, true);
});

test("other documentation pages need no form", () => {
  vm.runInNewContext(source, { document: { getElementById: () => null } });
});
