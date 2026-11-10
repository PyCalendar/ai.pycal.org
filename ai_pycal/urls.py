"""The addresses of the pages."""

from allauth.account import views as account_views
from django.contrib import admin
from django.urls import include, path

from .views import agreements, pages, policies, profile, setup, webhook

urlpatterns = [
    path("", pages.home, name="home"),
    path("health/", pages.health, name="health"),
    path("favicon.ico", pages.favicon, name="favicon"),
    path("projects/", policies.projects, name="projects"),
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
    path("accounts/", include("allauth.urls")),
    path("admin/", admin.site.urls),
    path("<str:owner>/<str:repo>/", setup.repository, name="repository"),
    path(
        "<str:owner>/<str:repo>/pull/<int:number>/",
        policies.pull,
        name="pull_request",
    ),
]
