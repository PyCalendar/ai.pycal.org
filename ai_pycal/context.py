"""What every page knows: the name of the site, its colors and its links."""

from django.conf import settings
from django.db.models import Q

from .models import ProjectProblem
from .services.identity import GitHubIdentity


def site(request) -> dict:
    """The context of every template.

    Args:
        request: The request.

    Returns:
        The name, the colors, the links of the site and the GitHub account of the visitor.
    """
    docs = settings.DOCS_URL.rstrip("/") + "/"
    problems = []
    if getattr(request.user, "is_authenticated", False):
        problems = (
            ProjectProblem.objects.filter(
                Q(repository__watchers=request.user)
                | Q(repository__installation__admins=request.user),
                active=True,
            )
            .select_related("repository")
            .distinct()
        )
    return {
        "site_name": settings.SITE_NAME,
        "theme_css": settings.THEME.stylesheet(),
        "extra_css_url": settings.EXTRA_CSS_URL,
        "links": {
            "documentation": docs,
            "sign": f"{docs}tutorial/sign.html",
            "admin_tutorial": f"{docs}tutorial/admin.html",
            "app_setup": f"{docs}how-to/github-app.html",
            "app_manifest_tutorial": f"{docs}how-to/github-app-manifest.html",
            "app_create": f"{docs}how-to/create-github-app.html",
            "app_manual_tutorial": f"{docs}how-to/github-app-manual.html",
            "config_file": f"{docs}reference/config-file.html",
            "changelog": f"{docs}changelog.html",
            "source": settings.SOURCE_URL,
            "issues": f"{settings.SOURCE_URL.rstrip('/')}/issues/new",
        },
        "github": GitHubIdentity.of(getattr(request, "user", None)),
        "project_problems": problems,
        "focused": "/pulls/" in request.path
        or "/pulls/" in request.GET.get("next", request.POST.get("next", "")),
    }
