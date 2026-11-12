"""The addresses of the pages."""

from allauth.account import views as account_views
from django.contrib import admin
from django.urls import include, path

from .views import agreements, pages, policies, profile, registration, setup, webhook

urlpatterns = [
    path("", pages.home, name="home"),
    path("about/", pages.about, name="about"),
    path("health/", pages.health, name="health"),
    path("favicon.ico", pages.favicon, name="favicon"),
    path("theme/", pages.theme, name="theme"),
    path("projects/", policies.projects, name="projects"),
    path("projects/<str:owner>/", policies.projects, name="owner_projects"),
    path("contributor/<str:handle>/", policies.contributor, name="contributor"),
    path("profile/", profile.profile, name="profile"),
    path("agreements/", policies.histories, name="histories"),
    path("my-agreements/", agreements.mine, name="mine"),
    path(
        "agreements/history/<str:owner>/<str:repo>/<path:agreement_path>/",
        policies.history,
        name="history",
    ),
    path("project/<str:owner>/<str:repo>/", policies.project, name="project"),
    path("project/<str:owner>/<str:repo>/default/", policies.default_choice, name="default_choice"),
    path("project/<str:owner>/<str:repo>/pulls/<int:number>/", policies.pull, name="project_pull"),
    path(
        "project/<str:owner>/<str:repo>/pulls/<int:number>/choice/", policies.choose, name="choose"
    ),
    path(
        "project/<str:owner>/<str:repo>/pulls/<int:number>/sign/",
        policies.sign_pull,
        name="sign_pull",
    ),
    path(
        "project/<str:owner>/<str:repo>/contributor/<str:handle>/<str:policy>.json",
        policies.policy_status,
        name="policy_json",
    ),
    path(
        "project/<str:owner>/<str:repo>/contributor/<str:handle>/<str:policy>.svg",
        policies.policy_status,
        {"badge": True},
        name="policy_badge",
    ),
    path("agreements/<int:pk>/", agreements.show, name="agreement"),
    path("agreements/<int:pk>/sign/", agreements.sign, name="sign"),
    path("agreements/<int:pk>/changes/<int:old>/", agreements.changes, name="changes"),
    path("setup/", setup.setup, name="setup"),
    path("setup/installed/", setup.installed, name="installed"),
    path("setup/github-app/", registration.register_app, name="register_app"),
    path("setup/github-app/registered/", registration.app_registered, name="app_registered"),
    path("setup/<int:installation_id>/email/", setup.notify_email, name="notify_email"),
    path(
        "setup/<int:installation_id>/<int:repository_id>/add/",
        setup.add_repository,
        name="add_repository",
    ),
    path(
        "setup/<int:installation_id>/<int:repository_id>/remove/",
        setup.remove_repository,
        name="remove_repository",
    ),
    path("github/webhook/", webhook.webhook, name="webhook"),
    path("accounts/email/", account_views.email, name="account_email"),
    path(
        "accounts/confirm-email/",
        account_views.email_verification_sent,
        name="account_email_verification_sent",
    ),
    path(
        "accounts/confirm-email/<str:key>/",
        account_views.confirm_email,
        name="account_confirm_email",
    ),
    # before allauth: GitHub also returns here after installations (views/setup.py)
    path("accounts/github/login/callback/", setup.github_callback, name="github_callback_install"),
    path("accounts/", include("allauth.urls")),
    path("admin/", admin.site.urls),
    path("repository/<str:owner>/<str:repo>/", setup.repository, name="repository"),
    path(
        "repository/<str:owner>/<str:repo>/pull/<int:number>/",
        policies.pull,
        name="pull_request",
    ),
    # The older addresses, without "repository/", which links may still use; last, so that
    # every page of the site takes precedence over an owner of the same name.
    path("<str:owner>/<str:repo>/", setup.older_address),
    path("<str:owner>/<str:repo>/pull/<int:number>/", setup.older_address),
]

handler400 = "ai_pycal.views.errors.bad_request"
handler403 = "ai_pycal.views.errors.permission_denied"
handler404 = "ai_pycal.views.errors.page_not_found"
handler500 = "ai_pycal.views.errors.server_error"
