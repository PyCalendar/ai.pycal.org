"""Restrict public directories and agreement text to visible projects."""

from django.db.models import Q

from ai_pycal.models import Repository

from .identity import GitHubIdentity


def visible_projects(user):
    """List public projects and private projects already associated with this user.

    Args:
        user: The visitor, possibly anonymous.

    Returns:
        A distinct repository queryset.
    """
    allowed = Q(private=False)
    identity = GitHubIdentity.of(user)
    if identity:
        allowed |= (
            Q(watchers=user)
            | Q(installation__admins=user)
            | Q(pull_requests__author_github_id=identity.github_id)
        )
    return Repository.objects.filter(allowed).distinct()
