"""Each agreement of a configuration file can ask for its own reading time."""

import time

import pytest
from django.core import signing

from ai_pycal import errors
from ai_pycal.config.agreement_spec import AgreementSpec
from ai_pycal.config.remote import GitHubRemote
from ai_pycal.models import RequiredAgreement
from ai_pycal.services.signer import SALT, Signer

HOME = GitHubRemote("o", "r")


def spec(**extra):
    return AgreementSpec.parse("cla", {"name": "CLA", "path": "cla.md", **extra}, HOME)


def test_the_reading_time_is_read():
    assert spec(**{"sign-min-seconds": 30}).sign_min_seconds == 30.0
    assert spec(**{"sign-min-seconds": 0}).sign_min_seconds == 0.0
    assert spec(**{"sign-min-seconds": 2.5}).sign_min_seconds == 2.5
    assert spec().sign_min_seconds is None


@pytest.mark.parametrize("value", ["30", True, -1, 3601, [30], {"s": 1}])
def test_an_invalid_reading_time_is_refused(value):
    with pytest.raises(errors.InvalidSignMinSeconds):
        spec(**{"sign-min-seconds": value})


def test_version_1_does_not_know_the_reading_time():
    with pytest.raises(errors.UnknownConfigKey):
        AgreementSpec.parse(
            "cla",
            {"name": "CLA", "path": "cla.md", "pr": {"tags": []}, "sign-min-seconds": 3},
            HOME,
            legacy=True,
        )


@pytest.mark.django_db
class TestSigning:
    @pytest.fixture
    def cla(self, repository):
        return RequiredAgreement.objects.get(repository=repository, key="cla")

    def token(self, version, alice, seconds_ago):
        identity = alice.socialaccount_set.get()
        return signing.dumps(
            {"v": version.pk, "g": int(identity.uid), "t": time.time() - seconds_ago}, salt=SALT
        )

    def test_the_site_setting_without_the_key(self, cla, settings):
        settings.SIGN_MIN_SECONDS = 3
        assert Signer.reading_time(cla.version) == 3

    def test_the_longest_time_of_the_projects(self, cla, settings):
        settings.SIGN_MIN_SECONDS = 3
        cla.sign_min_seconds = 20
        cla.save()
        assert Signer.reading_time(cla.version) == 20
        cla.sign_min_seconds = 0
        cla.save()
        assert Signer.reading_time(cla.version) == 0

    def test_signing_before_the_reading_time_is_refused(self, client, cla, alice, settings):
        cla.sign_min_seconds = 60
        cla.save()
        client.force_login(alice)
        response = client.post(
            f"/agreements/{cla.version_id}/sign/",
            {"accept": "yes", "handle": "alice", "shown": self.token(cla.version, alice, 10)},
        )
        assert response.status_code == 400
        assert 'data-error="SignedTooFast"' in response.content.decode()
        response = client.post(
            f"/agreements/{cla.version_id}/sign/",
            {"accept": "yes", "handle": "alice", "shown": self.token(cla.version, alice, 61)},
        )
        assert response.status_code == 302

    def test_the_gear_shows_the_reading_time(self, client, cla):
        assert (
            "data-reading-time" not in client.get(f"/agreements/{cla.version_id}/").content.decode()
        )
        cla.sign_min_seconds = 30
        cla.save()
        page = client.get(f"/agreements/{cla.version_id}/").content.decode()
        assert "At least 30 seconds before signing" in page

    def test_the_sync_keeps_the_reading_time(self, repository, github, cla):
        from ai_pycal.services.repository_sync import RepositorySync
        from tests.conftest import DATA, REPOSITORY

        config = (DATA / "agreements.yml").read_text().replace("version: 2.1.0", "version: 2.2.0")
        config = config.replace("  cla:\n", "  cla:\n    sign-min-seconds: 45\n", 1)
        github.push(REPOSITORY, {".github/agreements.yml": config})
        RepositorySync(repository).sync()
        cla.refresh_from_db()
        assert cla.sign_min_seconds == 45
