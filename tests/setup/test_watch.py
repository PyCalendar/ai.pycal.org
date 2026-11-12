"""Watching a project: needs a verified email; emails go to one verified address."""

import pytest
from allauth.account.models import EmailAddress

from ai_pycal.services.email_addresses import notification_addresses
from tests.conftest import REPOSITORY

pytestmark = pytest.mark.django_db
URL = f"/project/{REPOSITORY}/"


def test_watching_needs_a_verified_address(client, repository, alice):
    client.force_login(alice)
    page = client.get(URL).content.decode()
    assert "Needs a verified email address." in page
    client.post(f"{URL}watch/", {"watch": "yes"})
    assert not repository.watchers.filter(pk=alice.pk).exists()
    assert "Verify an email address first" in client.get(URL).content.decode()


def test_watch_and_stop(client, repository, alice):
    EmailAddress.objects.create(user=alice, email="alice@example.org", primary=True, verified=True)
    client.force_login(alice)
    client.post(f"{URL}watch/", {"watch": "yes"})
    assert repository.watchers.filter(pk=alice.pk).exists()
    page = client.get(URL).content.decode()
    watchers = page.split("data-watchers>")[1].split("</span>")[0]
    assert "go to the people who watch it:" in watchers
    assert '<a href="/contributor/alice/">@alice</a>' in watchers
    assert "alice@example.org" not in watchers  # the addresses are private
    client.post(f"{URL}watch/", {"watch": "no"})
    assert not repository.watchers.filter(pk=alice.pk).exists()


def test_one_verified_address_per_person(alice, bob):
    EmailAddress.objects.create(user=alice, email="old@example.org", primary=False, verified=True)
    EmailAddress.objects.create(user=alice, email="main@example.org", primary=True, verified=True)
    assert notification_addresses([alice.pk]) == ["main@example.org"]


def test_an_unverified_primary_keeps_the_verified_address(alice):
    EmailAddress.objects.create(
        user=alice, email="checked@example.org", primary=False, verified=True
    )
    EmailAddress.objects.create(user=alice, email="new@example.org", primary=True, verified=False)
    assert notification_addresses([alice.pk]) == ["checked@example.org"]


def test_people_who_turned_emails_off_get_none(alice):
    from ai_pycal.models import Profile

    EmailAddress.objects.create(user=alice, email="a@example.org", primary=True, verified=True)
    Profile.objects.update_or_create(user=alice, defaults={"email_notifications": False})
    assert notification_addresses([alice.pk]) == []


def test_watchers_get_the_email_of_a_problem(client, github, repository, alice, mailoutbox):
    from ai_pycal.services.repository_sync import RepositorySync

    EmailAddress.objects.create(user=alice, email="alice@example.org", primary=True, verified=True)
    repository.watchers.add(alice)
    github.push(REPOSITORY, {".github/agreements.yml": "version: 9.0.0\n"})
    with pytest.raises(Exception):
        RepositorySync(repository).sync()
    assert any("alice@example.org" in mail.to for mail in mailoutbox)


def test_the_handles_of_all_watchers_are_listed(client, repository, alice, bob, maintainer):
    repository.watchers.add(alice, bob)
    client.force_login(bob)
    watchers = client.get(URL).content.decode().split("data-watchers>")[1].split("</span>")[0]
    assert "@alice</a>, " in watchers and "@bob</a>" in watchers
    assert "@maintainer" not in watchers
    assert "You have no verified email address yet." in watchers  # bob has none


def test_the_page_of_a_project_lists_no_watchers_to_visitors(client, repository, alice):
    repository.watchers.add(alice)
    assert "data-watchers" not in client.get(URL).content.decode()
