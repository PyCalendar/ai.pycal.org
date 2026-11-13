"""The people of SITE_ADMINS may open the Django admin, also with a session of before."""

import pytest
from django.contrib.auth import get_user_model

pytestmark = pytest.mark.django_db


def test_a_site_admin_who_signed_in_before_opens_the_django_admin(client, maintainer, settings):
    settings.SITE_ADMINS = []
    client.force_login(maintainer)
    assert client.get("/admin/").status_code == 302  # not yet an administrator
    settings.SITE_ADMINS = ["maintainer"]  # added while signed in
    assert client.get("/admin/").status_code == 200
    maintainer.refresh_from_db()
    assert maintainer.is_staff and maintainer.is_superuser


def test_a_person_removed_from_site_admins_loses_the_django_admin(client, maintainer, settings):
    settings.SITE_ADMINS = ["maintainer"]
    client.force_login(maintainer)
    assert client.get("/admin/").status_code == 200
    settings.SITE_ADMINS = []
    response = client.get("/admin/")
    assert response.status_code == 302 and "/admin/login/" in response["Location"]
    maintainer.refresh_from_db()
    assert not maintainer.is_staff and not maintainer.is_superuser


def test_a_superuser_without_github_keeps_the_django_admin(client, settings):
    settings.SITE_ADMINS = []
    root = get_user_model().objects.create(username="root", is_staff=True, is_superuser=True)
    client.force_login(root)
    assert client.get("/admin/").status_code == 200
    root.refresh_from_db()
    assert root.is_superuser


def test_the_handle_is_compared_without_case(client, maintainer, settings):
    settings.SITE_ADMINS = ["maintainer"]
    maintainer.socialaccount_set.update(extra_data={"login": "MainTainer"})
    client.force_login(maintainer)
    assert client.get("/admin/").status_code == 200
