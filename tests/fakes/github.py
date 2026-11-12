"""A fake GitHub: the tests never use the network.

It knows repositories with commits and files, installations, pull requests, labels
and statuses, and answers the requests the site sends with httpx.
"""

import base64
import hashlib
import itertools
import json
import re
from dataclasses import dataclass, field
from urllib.parse import parse_qs, unquote

import httpx

_counter = itertools.count(1)


def new_sha(seed: str = "") -> str:
    """A new commit SHA."""
    return hashlib.sha1(f"{seed}{next(_counter)}".encode()).hexdigest()


@dataclass
class FakeRepository:
    full_name: str
    id: int
    default_branch: str = "main"
    private: bool = False
    refs: dict[str, str] = field(default_factory=dict)  # ref: sha
    trees: dict[str, dict[str, bytes]] = field(default_factory=dict)  # sha: path: content
    parents: dict[str, str | None] = field(default_factory=dict)

    def as_json(self) -> dict:
        return {
            "id": self.id,
            "full_name": self.full_name,
            "name": self.full_name.split("/")[1],
            "owner": {"login": self.full_name.split("/")[0]},
            "private": self.private,
            "default_branch": self.default_branch,
            "html_url": f"https://github.com/{self.full_name}",
        }


class FakeGitHub:
    """The state of the fake GitHub and the handler of httpx."""

    def __init__(self):
        self.repositories: dict[str, FakeRepository] = {}
        self.installations: dict[int, dict] = {}
        self.installation_repositories: dict[int, list[str]] = {}
        self.user_installations: list[int] = []
        self.user_roles: dict[str, dict] = {}  # full_name: permissions of the user
        self.labels: dict[tuple[str, int], list[str]] = {}
        self.statuses: list[dict] = []
        self.pulls: dict[str, list[dict]] = {}
        self.requests: list[httpx.Request] = []
        self.fail_with: int | None = None  # answer every request with this status
        self.unreachable = False
        self.refresh_tokens = {"refresh-token"}
        self.oauth_response: httpx.Response | None = None
        # code of a registration: the app that GitHub created from the manifest
        self.manifest_codes: dict[str, dict] = {}

    # --- setting up the state -------------------------------------------------

    def repository(self, full_name: str, **kwargs) -> FakeRepository:
        if full_name not in self.repositories:
            self.repositories[full_name] = FakeRepository(
                full_name, id=1000 + len(self.repositories), **kwargs
            )
        return self.repositories[full_name]

    def push(self, full_name: str, files: dict[str, str | bytes | None], ref: str = "") -> str:
        """Commit files to a branch (the default branch by default); None deletes a file."""
        repo = self.repository(full_name)
        branch = ref or repo.default_branch
        old = repo.trees.get(repo.refs.get(branch, ""), {})
        tree = dict(old)
        for path, content in files.items():
            if content is None:
                tree.pop(path, None)
            else:
                tree[path] = content.encode() if isinstance(content, str) else content
        sha = new_sha(full_name)
        repo.parents[sha] = repo.refs.get(branch)
        repo.trees[sha] = tree
        repo.refs[branch] = sha
        if branch == repo.default_branch:
            repo.refs["HEAD"] = sha
        return sha

    def tag(self, full_name: str, tag: str, sha: str) -> None:
        self.repository(full_name).refs[tag] = sha

    def install(
        self,
        installation_id: int,
        account: str,
        repositories: list[str],
        permissions: dict | None = None,
        account_type: str = "Organization",
    ) -> dict:
        from ai_pycal.github.permissions import REQUIRED

        data = {
            "id": installation_id,
            "account": {"login": account, "type": account_type},
            "permissions": dict(REQUIRED) if permissions is None else permissions,
            "html_url": f"https://github.com/organizations/{account}/settings/installations/{installation_id}",
            "suspended_at": None,
        }
        self.installations[installation_id] = data
        self.installation_repositories[installation_id] = list(repositories)
        for name in repositories:
            self.repository(name)
        return data

    def open_pull(
        self, full_name: str, number: int, author: tuple[int, str], sha: str = ""
    ) -> dict:
        data = {
            "number": number,
            "title": f"Pull request {number}",
            "state": "open",
            "user": {"id": author[0], "login": author[1], "type": "User"},
            "head": {"sha": sha or new_sha("head")},
        }
        self.pulls.setdefault(full_name, []).append(data)
        return data

    def status(self, full_name: str, sha: str, context: str) -> dict | None:
        found = [
            s
            for s in self.statuses
            if s["repo"] == full_name and s["sha"] == sha and s["context"] == context
        ]
        return found[-1] if found else None

    # --- answering -------------------------------------------------------------

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handle)

    ROUTES = [
        ("POST", r"/app-manifests/(?P<code>[^/]+)/conversions", "manifest_conversion"),
        ("POST", r"/login/oauth/access_token", "refresh_user_token"),
        ("POST", r"/app/installations/(?P<id>\d+)/access_tokens", "access_token"),
        ("GET", r"/app/installations/(?P<id>\d+)", "installation"),
        ("GET", r"/installation/repositories", "list_installation_repositories"),
        ("GET", r"/user/installations", "list_user_installations"),
        ("GET", r"/user/installations/(?P<id>\d+)/repositories", "list_user_repositories"),
        ("GET", r"/repos/(?P<repo>[^/]+/[^/]+)/commits/(?P<ref>.+)", "commit"),
        ("GET", r"/repos/(?P<repo>[^/]+/[^/]+)/commits", "file_history"),
        ("GET", r"/repos/(?P<repo>[^/]+/[^/]+)/contents/(?P<path>.+)", "contents"),
        ("GET", r"/repos/(?P<repo>[^/]+/[^/]+)/issues/(?P<n>\d+)/labels", "get_labels"),
        ("POST", r"/repos/(?P<repo>[^/]+/[^/]+)/issues/(?P<n>\d+)/labels", "add_labels"),
        (
            "DELETE",
            r"/repos/(?P<repo>[^/]+/[^/]+)/issues/(?P<n>\d+)/labels/(?P<label>.+)",
            "remove_label",
        ),
        ("POST", r"/repos/(?P<repo>[^/]+/[^/]+)/statuses/(?P<sha>\w+)", "set_status"),
        ("GET", r"/repos/(?P<repo>[^/]+/[^/]+)/pulls", "list_pulls"),
    ]

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.unreachable:
            raise httpx.ConnectError("no network", request=request)
        if self.fail_with:
            return httpx.Response(self.fail_with, json={"message": "failure of the fake"})
        path = request.url.path
        for method, pattern, name in self.ROUTES:
            match = re.fullmatch(pattern, path)
            if method == request.method and match:
                return getattr(self, name)(request, **match.groupdict())
        return self.not_found()

    @staticmethod
    def not_found() -> httpx.Response:
        return httpx.Response(404, json={"message": "Not Found"})

    @staticmethod
    def token(request: httpx.Request) -> str:
        return request.headers.get("Authorization", "").removeprefix("Bearer ")

    def manifest_conversion(self, request, code):
        """Give the credentials of a new app once, as GitHub does; then the code is gone."""
        if code not in self.manifest_codes:
            return self.not_found()
        return httpx.Response(201, json=self.manifest_codes.pop(code))

    def access_token(self, request, id):
        if int(id) not in self.installations:
            return self.not_found()
        return httpx.Response(
            201, json={"token": f"installation-{id}", "expires_at": "2099-01-01T00:00:00Z"}
        )

    def refresh_user_token(self, request):
        """Exchange a refresh token once, as GitHub does when rotating tokens."""
        if self.oauth_response is not None:
            return self.oauth_response
        data = parse_qs(request.content.decode())
        if data.get("client_id") != ["client"] or data.get("client_secret") != ["secret"]:
            return httpx.Response(200, json={"error": "incorrect_client_credentials"})
        assert data.get("grant_type") == ["refresh_token"]
        refresh = data.get("refresh_token", [""])[0]
        if refresh not in self.refresh_tokens:
            return httpx.Response(200, json={"error": "bad_refresh_token"})
        self.refresh_tokens.remove(refresh)
        replacement = refresh + "-next"
        self.refresh_tokens.add(replacement)
        return httpx.Response(
            200,
            json={
                "access_token": "user-token",
                "refresh_token": replacement,
                "expires_in": 28800,
                "refresh_token_expires_in": 15897600,
            },
        )

    def installation(self, request, id):
        if int(id) not in self.installations:
            return self.not_found()
        return httpx.Response(200, json=self.installations[int(id)])

    def installation_id_of(self, request) -> int:
        return int(self.token(request).removeprefix("installation-"))

    def list_installation_repositories(self, request):
        names = self.installation_repositories.get(self.installation_id_of(request), [])
        repos = [self.repositories[name].as_json() for name in names]
        return httpx.Response(200, json={"total_count": len(repos), "repositories": repos})

    def list_user_installations(self, request):
        if self.token(request) != "user-token":
            return httpx.Response(401, json={"message": "Bad credentials"})
        found = [self.installations[i] for i in self.user_installations if i in self.installations]
        return httpx.Response(200, json={"total_count": len(found), "installations": found})

    def list_user_repositories(self, request, id):
        if self.token(request) != "user-token":
            return httpx.Response(401, json={"message": "Bad credentials"})
        if int(id) not in self.user_installations:
            return httpx.Response(403, json={"message": "Forbidden"})
        repos = []
        for name in self.installation_repositories.get(int(id), []):
            data = self.repositories[name].as_json()
            data["permissions"] = self.user_roles.get(name, {"admin": True})
            repos.append(data)
        return httpx.Response(200, json={"total_count": len(repos), "repositories": repos})

    def repo_or_none(self, request, repo) -> FakeRepository | None:
        found = self.repositories.get(repo)
        if found is None:
            return None
        if found.private and self.token(request).startswith("installation-"):
            installation = self.installation_id_of(request)
            if repo not in self.installation_repositories.get(installation, []):
                return None
        return found

    def commit(self, request, repo, ref):
        found = self.repo_or_none(request, repo)
        ref = unquote(ref)
        if found is None:
            return self.not_found()
        sha = found.refs.get(ref) or (ref if ref in found.trees else None)
        if sha is None:
            return self.not_found()
        return httpx.Response(200, json={"sha": sha})

    def contents(self, request, repo, path):
        found = self.repo_or_none(request, repo)
        path = unquote(path)
        if found is None:
            return self.not_found()
        sha = request.url.params.get("ref", "")
        tree = found.trees.get(found.refs.get(sha, sha), {})
        if path not in tree:
            if any(name.startswith(path + "/") for name in tree):
                return httpx.Response(200, json=[{"type": "file", "path": path + "/x"}])
            return self.not_found()
        content = tree[path]
        return httpx.Response(
            200,
            json={
                "type": "file",
                "path": path,
                "size": len(content),
                "encoding": "base64",
                "content": base64.b64encode(content).decode(),
            },
        )

    def file_history(self, request, repo):
        """Return the last actual change to a path in the selected ancestry."""
        found = self.repo_or_none(request, repo)
        if found is None:
            return self.not_found()
        ref = request.url.params.get("sha", "HEAD")
        sha = found.refs.get(ref, ref)
        if sha not in found.trees:
            return self.not_found()
        path = request.url.params["path"]
        while sha:
            parent = found.parents.get(sha)
            previous = found.trees.get(parent, {})
            if found.trees[sha].get(path) != previous.get(path):
                return httpx.Response(200, json=[{"sha": sha}])
            sha = parent
        return httpx.Response(200, json=[])

    def get_labels(self, request, repo, n):
        labels = self.labels.get((repo, int(n)), [])
        return httpx.Response(200, json=[{"name": name} for name in labels])

    def add_labels(self, request, repo, n):
        labels = self.labels.setdefault((repo, int(n)), [])
        for name in json.loads(request.content)["labels"]:
            if name not in labels:
                labels.append(name)
        return httpx.Response(200, json=[{"name": name} for name in labels])

    def remove_label(self, request, repo, n, label):
        labels = self.labels.get((repo, int(n)), [])
        label = unquote(label)
        if label not in labels:
            return self.not_found()
        labels.remove(label)
        return httpx.Response(200, json=[{"name": name} for name in labels])

    def set_status(self, request, repo, sha):
        if (
            self.installations.get(self.installation_id_of(request), {})
            .get("permissions", {})
            .get("statuses")
            != "write"
        ):
            return httpx.Response(403, json={"message": "Resource not accessible by integration"})
        data = json.loads(request.content)
        self.statuses.append({"repo": repo, "sha": sha, **data})
        return httpx.Response(201, json=data)

    def list_pulls(self, request, repo):
        page = int(request.url.params.get("page", "1"))
        pulls = self.pulls.get(repo, []) if page == 1 else []
        return httpx.Response(200, json=[p for p in pulls if p["state"] == "open"])
