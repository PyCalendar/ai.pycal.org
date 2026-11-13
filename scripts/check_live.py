"""Check a running site from outside, as a visitor who is not signed in.

Usage: ``make check-live``, or ``LIVE_URL=https://sign.example.org make check-live``.
``LIVE_URL`` is not ``SITE_URL``, so that the setting of a local site does not change it.

The check

1. waits while the site starts or is updated (5xx or no connection), up to ``LIVE_WAIT`` seconds;
2. opens the public pages and takes a public project from the page Projects;
3. follows every link from there that leads to a public page (the project, its pull requests,
   agreements, versions, contributors, logs and badges) and expects each to open without
   signing in;
4. reads the JSON of every public page, ``<page>.json``, which other sites may read (CORS);
5. checks that errors get their pages: a missing page is 404, not 500, pages that need
   privileges ask to sign in or answer 403, and the webhook refuses unsigned deliveries.

It only reads, except for one unsigned webhook delivery, which the site refuses and logs.
"""

import os
import re
import sys
import time
import uuid
from collections import deque
from urllib.parse import urljoin, urlsplit

import httpx

DEFAULT_URL = "https://sign.pycal.org"
# the pages without personal information or configuration that needs privileges
PUBLIC = re.compile(
    r"^/(|about/|licenses/.*|projects/.*|project/.*|contributor/.*|agreements/.*|logs/(?!all/).*"
    r"|health/|favicon\.ico|accounts/login/)$"
)
# links that are not pages to check: leaving the site, signing out, the admin and setup
SKIP = re.compile(r"^/(accounts/(?!login/$)|admin/|setup/|static/|theme/|github/)")
SIGN_IN = "/accounts/login/"
# pages that act for a person, such as signing: they ask visitors to sign in
PERSONAL = re.compile(r"^/(project/.*/sign/|agreements/\d+/sign/|my-agreements/|todos/|profile/)$")
MAX_PAGES = 300
TRIES = 3  # tries of a request that gets no answer, such as a timeout
RETRY_PAUSE = 10


class LiveCheck:
    """Walk the public pages of a site and check its error pages."""

    def __init__(self, url: str, client: httpx.Client | None = None, wait: float = 600):
        """The check of the site at *url*.

        Args:
            url: The address of the site, such as ``https://sign.pycal.org``.
            client: The HTTP client; one without redirects by default.
            wait: How long to wait for the site to start, in seconds.
        """
        self.url = url.rstrip("/")
        self.client = client or httpx.Client(timeout=30, follow_redirects=False)
        self.wait = wait
        self.failures: list[str] = []
        self.checked: dict[str, int] = {}

    def report(self, ok: bool, status: int | str, path: str, note: str = "") -> None:
        """Print one result and keep the failures.

        Args:
            ok: Whether the result is as expected.
            status: The HTTP status, or what happened.
            path: The page.
            note: What was expected, for failures.
        """
        line = f"{'ok  ' if ok else 'FAIL'} {status} {path}" + (f"  ({note})" if note else "")
        print(line, flush=True)
        if not ok:
            self.failures.append(line)

    def get(self, path: str) -> httpx.Response:
        """GET a page of the site, without following redirects.

        Args:
            path: The path, such as ``/about/``.

        Returns:
            The answer; one with the status 599 and the reason if there was none after
            ``TRIES`` tries, such as after timeouts while the site is busy after a restart.
        """
        address = urljoin(self.url + "/", path.lstrip("/"))
        for attempt in range(TRIES):
            try:
                return self.client.get(address)
            except httpx.TransportError as error:
                reason = f"{type(error).__name__}: {error}"
                print(f"retry {path}: {reason}", flush=True)
                if attempt + 1 < TRIES:
                    time.sleep(RETRY_PAUSE)
        return httpx.Response(599, text=reason)

    def wait_until_up(self, pause: float = 10) -> bool:
        """Wait while the site starts: 5xx answers and refused connections are retried.

        Args:
            pause: Seconds between the tries.

        Returns:
            True when /health/ answers 200 within the time.
        """
        end = time.monotonic() + self.wait
        while True:
            try:
                status = self.get("/health/").status_code
            except httpx.HTTPError as error:
                status = type(error).__name__
            if status == 200:
                return True
            if time.monotonic() >= end:
                self.report(False, status, "/health/", f"the site did not start in {self.wait:g} s")
                return False
            print(f"wait {status} /health/: the site is starting", flush=True)
            time.sleep(pause)

    @staticmethod
    def links(html: str) -> list[str]:
        """The paths of the links of a page to pages of the same site.

        Args:
            html: The page.

        Returns:
            The paths, without queries and fragments, in their order.

        Examples:
            >>> LiveCheck.links('<a href="/about/">a</a> <a href="https://x.org/">b</a>'
            ...                 '<a href="/projects/#top">c</a> <a href="/about/?next=/">d</a>')
            ['/about/', '/projects/']
        """
        found = []
        for href in re.findall(r'href="([^"]+)"', html):
            href = href.replace("&amp;", "&")
            parts = urlsplit(href)
            if parts.scheme or parts.netloc or not parts.path.startswith("/"):
                continue
            if parts.path not in found:  # each page once: queries such as ?next= repeat it
                found.append(parts.path)
        return found

    def check_page(self, path: str) -> str | None:
        """Open a public page: it must open without signing in.

        Args:
            path: The page.

        Returns:
            The HTML of the page, or None if it failed.
        """
        response = self.get(path)
        self.checked[path] = response.status_code
        location = response.headers.get("location", "")
        if response.status_code == 200:
            text = response.text
            if "Traceback" in text or "Server Error" in text:
                self.report(False, 200, path, "the page shows a server error")
                return None
            self.report(True, 200, path)
            if "html" not in response.headers.get("content-type", ""):
                return ""
            self.check_json(path)
            return text
        if response.status_code in (301, 302) and SIGN_IN in location:
            self.report(False, response.status_code, path, "public, but asks to sign in")
        elif response.status_code in (301, 302, 307, 308):
            target = urlsplit(urljoin(self.url + path, location))
            # the icon may be an address elsewhere (the setting FAVICON)
            same = f"{target.scheme}://{target.netloc}" == self.url or path == "/favicon.ico"
            self.report(same, response.status_code, path, "" if same else f"leaves to {location}")
            return None
        else:
            self.report(False, response.status_code, path, "expected 200")
        return None

    def check_json(self, path: str) -> None:
        """Read the JSON of a public page: it must be JSON that other sites may read.

        Args:
            path: The page, such as ``/projects/``.
        """
        address = "/index.json" if path == "/" else path.rstrip("/") + ".json"
        if path == SIGN_IN:
            return
        response = self.get(address)
        self.checked[address] = response.status_code
        problem = ""
        if response.status_code != 200:
            problem = "expected 200"
        elif not response.headers.get("content-type", "").startswith("application/json"):
            problem = "not JSON"
        elif response.headers.get("access-control-allow-origin") != "*":
            problem = "other sites may not read it (CORS)"
        else:
            try:
                response.json()
            except ValueError:
                problem = "invalid JSON"
        self.report(not problem, response.status_code, address, problem)

    def walk(self, start: list[str]) -> None:
        """Follow the links of the public pages, from *start*.

        Args:
            start: The first pages.
        """
        queue = deque(start)
        seen = set(start)
        while queue and len(self.checked) < MAX_PAGES:
            path = queue.popleft()
            html = self.check_page(path)
            for link in self.links(html or ""):
                if link in seen or SKIP.match(link):
                    continue
                if PERSONAL.match(link):
                    seen.add(link)
                    self.expect(link, (302,))
                    continue
                if not PUBLIC.match(link):
                    continue
                seen.add(link)
                queue.append(link)

    def project(self) -> str | None:
        """A public project of the page Projects.

        Returns:
            Its path, such as ``/project/PyCalendar/sign.pycal.org-example/``, or None.
        """
        found = re.findall(r'href="(/project/[^/"]+/[^/"]+/)"', self.get("/projects/").text)
        if not found:
            self.report(False, "-", "/projects/", "no public project is listed")
            return None
        print(f"project {found[0]}", flush=True)
        return found[0]

    def expect(self, path: str, statuses: tuple[int, ...], page: bool = True) -> None:
        """Check the answer of a page that is not public or does not exist.

        Args:
            path: The page.
            statuses: The statuses that are right.
            page: Whether the answer must be the page of the error of the site.
        """
        response = self.get(path)
        status = response.status_code
        ok = status in statuses
        note = f"expected {' or '.join(map(str, statuses))}"
        if ok and status in (301, 302):
            ok = any(
                address in response.headers.get("location", "")
                for address in (SIGN_IN, "/admin/login/")
            )
            note = "expected to ask to sign in"
        elif ok and page and status >= 400:
            ok = 'class="status-page' in response.text
            note = "expected the error page of the site"
        self.report(ok, status, path, "" if ok else note)

    def check_errors(self, project: str | None) -> None:
        """Errors get their pages, and pages that need privileges are not public.

        Args:
            project: A public project, for its missing pull request.
        """
        unknown = uuid.uuid4().hex[:12]
        for path in (
            f"/no-page-{unknown}/x/y/",
            "/agreements/999999999/",
            "/agreements/999999999/changes/1/",
            f"/project/nobody-{unknown}/nothing/",
            f"/projects/nobody-{unknown}/x/",
            "/licenses/no-such-license/",
            f"/licenses/packages/no-such-package-{unknown}/",
            f"/logs/nobody-{unknown}/nothing/",
        ):
            self.expect(path, (404,))
        if project:
            self.expect(f"{project}pulls/999999999/", (404,))
        for path in ("/setup/", "/profile/", "/my-agreements/", "/todos/"):
            self.expect(path, (302,))
        self.expect("/logs/all/", (302, 403))
        self.expect("/admin/", (302,), page=False)
        self.expect("/github/webhook/", (405,), page=False)
        response = self.client.post(
            f"{self.url}/github/webhook/",
            content=b"{}",
            headers={"X-GitHub-Event": "ping", "Content-Type": "application/json"},
        )
        refused = response.status_code == 401 and "WebhookSignatureMissing" in response.text
        self.report(
            refused,
            response.status_code,
            "POST /github/webhook/",
            "" if refused else "expected 401 WebhookSignatureMissing",
        )

    def run(self) -> int:
        """Check the site.

        Returns:
            The exit code: 0 if everything is right.
        """
        print(f"Checking {self.url}", flush=True)
        if not self.wait_until_up():
            return 1
        project = self.project()
        start = ["/", "/about/", "/licenses/", "/projects/", "/health/", "/favicon.ico", SIGN_IN]
        self.walk(start + ([project] if project else []))
        self.check_errors(project)
        print(
            f"{len(self.checked)} public pages and their JSON, {len(self.failures)} failures",
            flush=True,
        )
        for line in self.failures:
            print(line, flush=True)
        return 1 if self.failures else 0


if __name__ == "__main__":
    check = LiveCheck(
        os.environ.get("LIVE_URL") or DEFAULT_URL, wait=float(os.environ.get("LIVE_WAIT", 600))
    )
    sys.exit(check.run())
