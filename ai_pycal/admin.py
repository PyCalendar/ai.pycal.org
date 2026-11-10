"""The admin pages of Django, for the people of ``SITE_ADMINS``."""

from django.contrib import admin

from .models import (
    AgreementVersion,
    Installation,
    PullRequest,
    Repository,
    RequiredAgreement,
    Signature,
)


@admin.register(Installation)
class InstallationAdmin(admin.ModelAdmin):
    """The installations of the GitHub App."""

    list_display = ["account_login", "account_type", "removed", "suspended", "permissions_notified"]
    search_fields = ["account_login"]


@admin.register(Repository)
class RepositoryAdmin(admin.ModelAdmin):
    """The repositories."""

    list_display = ["full_name", "active", "config_version", "error_code", "checked"]
    list_filter = ["active", "error_code"]
    search_fields = ["full_name"]


@admin.register(AgreementVersion)
class AgreementVersionAdmin(admin.ModelAdmin):
    """The versions of agreements: they never change."""

    list_display = ["source", "path", "commit", "fetched"]
    search_fields = ["source", "path", "commit"]
    readonly_fields = ["source", "path", "commit", "text", "fetched"]


@admin.register(RequiredAgreement)
class RequiredAgreementAdmin(admin.ModelAdmin):
    """The agreements the repositories ask for."""

    list_display = ["repository", "key", "name", "ref", "mandatory", "version"]


@admin.register(Signature)
class SignatureAdmin(admin.ModelAdmin):
    """The signatures: they are made by people on the site only."""

    list_display = ["login", "github_id", "version", "signed"]
    search_fields = ["login"]
    readonly_fields = ["version", "github_id", "login", "user", "signed"]

    def has_add_permission(self, request) -> bool:
        """Nobody adds signatures for others.

        Args:
            request: The request.

        Returns:
            False.
        """
        return False


@admin.register(PullRequest)
class PullRequestAdmin(admin.ModelAdmin):
    """The pull requests the site knows."""

    list_display = ["repository", "number", "author_login", "open", "all_signed"]
    list_filter = ["open", "all_signed"]
