"""What every page knows: the name of the site, its colors and its links."""

from django.conf import settings
from django.db.models import Q
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from . import build_info
from .checks import is_url
from .models import ProjectProblem
from .services.app_registration import AppRegistration
from .services.identity import GitHubIdentity
from .services.todos import Todos
from .theme import COOKIE, Theme

# the choices of the menu of the colors: value, title and icon (ai_pycal/_theme_icon.html)
THEMES = (("auto", _("As the system")), ("light", _("Light")), ("dark", _("Dark")))


def is_flow(path: str) -> bool:
    """Whether an address is the signing flow of a pull request.

    Args:
        path: The path, such as ``/project/o/r/pulls/3/sign/``.

    Returns:
        True for the flow.

    Examples:
        >>> is_flow("/project/o/r/pulls/3/sign/"), is_flow("/project/o/r/pulls/3/")
        (True, False)
    """
    return "/pulls/" in path and path.rstrip("/").endswith("/sign")


def version_text() -> str:
    """The version and commit that run, for the details of errors.

    Returns:
        Such as ``1.2.3 (4cbfd3e)``.
    """
    build = build_info.get(settings.SOURCE_URL)
    if not build["commit"] or build["commit"] in build["version"]:
        return build["version"]
    return f"{build['version']} ({build['commit']})"


def site(request) -> dict:
    """The context of every template.

    Args:
        request: The request.

    Returns:
        The name, the colors (as chosen with the switch), the links of the site and the
        GitHub account of the visitor.
    """
    docs = settings.DOCS_URL.rstrip("/") + "/"
    problems = []
    todo_count = 0
    if getattr(request.user, "is_authenticated", False):
        todo_count = Todos(request.user, GitHubIdentity.of(request.user)).count()
        problems = (
            ProjectProblem.objects.filter(
                Q(repository__watchers=request.user)
                | Q(repository__installation__admins=request.user),
                active=True,
            )
            .select_related("repository")
            .distinct()
        )
    theme = Theme.choice(request.COOKIES.get(COOKIE))
    configured = bool(
        settings.GITHUB_APP_ID and settings.SOCIALACCOUNT_PROVIDERS["github"].get("APP")
    )
    return {
        "site_name": settings.SITE_NAME,
        "theme_choice": theme,
        "themes": THEMES,
        "color_scheme": "light dark" if theme == "auto" else theme,
        "theme_css": settings.THEME.stylesheet(theme),
        "extra_css_url": settings.EXTRA_CSS_URL,
        "favicon_url": settings.FAVICON if is_url(settings.FAVICON) else reverse("favicon"),
        "links": {
            "documentation": docs,
            "sign": f"{docs}tutorial/sign.html",
            "admin_tutorial": f"{docs}tutorial/admin.html",
            "app_setup": f"{docs}how-to/github-app.html",
            "app_manifest_tutorial": f"{docs}how-to/github-app-manifest.html",
            "app_create": f"{docs}how-to/create-github-app.html",
            "app_manual_tutorial": f"{docs}how-to/github-app-manual.html",
            "config_file": f"{docs}reference/config-file.html",
            "oauth_app": f"{docs}how-to/github-app-site.html#oauth-app",
            "permission_email": f"{docs}tutorial/admin.html#permission-email",
            "changelog": f"{docs}changelog.html",
            "source": settings.SOURCE_URL,
            "issues": f"{settings.SOURCE_URL.rstrip('/')}/issues/new",
        },
        "footer_links": settings.FOOTER_LINKS,
        "version": version_text(),
        # without an app, the sign-in page and the errors offer to register one
        "github_app_configured": configured,
        # why the site cannot register an app, shown instead of the button
        "app_registration_obstacle": None if configured else AppRegistration.obstacle(),
        "github": GitHubIdentity.of(getattr(request, "user", None)),
        "project_problems": problems,
        "todo_count": todo_count,
        "site_admin": GitHubIdentity.is_site_admin(request.user),
        "focused": "/pulls/" in request.path
        or "/pulls/" in request.GET.get("next", request.POST.get("next", "")),
        # the signing flow and the sign-in into it: nothing in the title bar leads away
        "flow": is_flow(request.path)
        or is_flow(request.GET.get("next", request.POST.get("next", ""))),
    }
