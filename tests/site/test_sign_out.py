"""People are signed out SIGN_OUT_MINUTES after signing in, also while they use the site."""

from datetime import timedelta

from allauth.account.signals import user_logged_in
from django.contrib.sessions.backends.db import SessionStore
from django.utils import timezone

from ai_pycal.signals import sign_out_later


def test_the_default_is_an_hour():
    from ai_pycal import settings

    assert settings.SIGN_OUT_MINUTES == 60
    assert settings.SESSION_COOKIE_AGE == 3600


def test_signing_in_sets_the_time_of_signing_out(rf, alice, settings):
    settings.SESSION_COOKIE_AGE = 3600
    request = rf.get("/")
    request.session = SessionStore()
    user_logged_in.send(sender=None, request=request, user=alice)
    expiry = request.session.get_expiry_date()
    assert timedelta(minutes=59) < expiry - timezone.now() <= timedelta(minutes=60)


def test_using_the_site_does_not_extend_the_time(rf, db, settings):
    settings.SESSION_COOKIE_AGE = 600
    request = rf.get("/")
    request.session = SessionStore()
    sign_out_later(request)
    fixed = request.session.get_expiry_date()
    request.session["something"] = "changed"
    request.session.save()
    assert SessionStore(request.session.session_key).get_expiry_date() == fixed


def test_a_request_without_a_session_is_left_alone(rf, alice):
    user_logged_in.send(sender=None, request=rf.get("/"), user=alice)


def test_after_the_time_the_person_is_signed_out(client, alice):
    client.force_login(alice)
    assert client.get("/profile/").status_code == 200
    session = client.session
    session.set_expiry(timezone.now() - timedelta(seconds=1))
    session.save()
    response = client.get("/profile/")
    assert response.status_code == 302 and "/accounts/login/" in response["Location"]
