"""The permissions the GitHub App needs, and which of them an installation lacks."""

# What this version of the site needs. When a new version needs more, the
# administrators of the installations are asked by email to accept them; the
# list is in docs/reference/permissions.rst (tests/github/test_permissions.py).
REQUIRED = {
    "metadata": "read",  # the repositories of the installation
    "contents": "read",  # the configuration file and the agreements
    "pull_requests": "write",  # the labels of the pull requests
    "statuses": "write",  # the checks of the pull requests, with a link to sign
}
# The events the app receives; "repository" needs only metadata: a new default branch, a
# repository renamed or transferred. An app subscribes to events in its settings on GitHub.
EVENTS = ["pull_request", "push", "repository"]
LEVELS = {"read": 1, "write": 2, "admin": 3}


def missing_events(subscribed: list[str]) -> list[str]:
    """The events of :data:`EVENTS` that the app does not receive.

    Args:
        subscribed: The events of the app, as ``GET /app`` lists them.

    Returns:
        The missing events, in the order of :data:`EVENTS`.

    Examples:
        >>> missing_events(["push", "pull_request"])
        ['repository']
    """
    return [event for event in EVENTS if event not in subscribed]


def missing(granted: dict[str, str], required: dict[str, str] | None = None) -> dict[str, str]:
    """The permissions an installation needs but was not granted.

    Args:
        granted: The permissions of the installation, as GitHub lists them.
        required: What is needed; :data:`REQUIRED` by default.

    Returns:
        The missing permissions with the level needed.

    Examples:
        >>> missing({"metadata": "read", "contents": "write"}, {"contents": "read"})
        {}
        >>> missing({"pull_requests": "read"}, {"pull_requests": "write", "statuses": "write"})
        {'pull_requests': 'write', 'statuses': 'write'}
    """
    required = REQUIRED if required is None else required
    return {
        name: level
        for name, level in required.items()
        if LEVELS.get(granted.get(name, ""), 0) < LEVELS[level]
    }


def describe(permissions: dict[str, str]) -> str:
    """The permissions as text, sorted, such as ``statuses:write``.

    Args:
        permissions: The permissions with their levels.

    Returns:
        The text; the same for the same permissions.

    Examples:
        >>> describe({"statuses": "write", "contents": "read"})
        'contents:read, statuses:write'
    """
    return ", ".join(f"{name}:{level}" for name, level in sorted(permissions.items()))


def manifest(name: str, url: str) -> dict:
    """The manifest of the GitHub App, to create it with these permissions and events.

    Args:
        name: The name of the app on GitHub.
        url: The address of the site.

    Returns:
        The manifest, as GitHub reads it.

    Examples:
        >>> manifest("ai.pycal.org", "https://ai.pycal.org")["hook_attributes"]["url"]
        'https://ai.pycal.org/github/webhook/'
    """
    return {
        "name": name,
        "url": url,
        "hook_attributes": {"url": f"{url}/github/webhook/", "active": True},
        "redirect_url": f"{url}/",
        "callback_urls": [f"{url}/accounts/github/login/callback/"],
        "setup_url": f"{url}/setup/installed/",
        "setup_on_update": True,
        # False: after an installation GitHub returns to setup_url (/setup/installed/); with
        # True it would return to the sign-in callback without the state of a sign-in
        "request_oauth_on_install": False,
        "public": True,
        "default_permissions": dict(REQUIRED),
        "default_events": list(EVENTS),
    }
