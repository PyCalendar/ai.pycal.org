"""Read the configuration file of a repository and the agreements it asks for."""

import logging

from django.db import transaction
from django.utils import timezone

from ai_pycal.actions import AgreementChanged, ConfigurationRead
from ai_pycal.config import CONFIG_PATH, GitHubRemote, RepositoryConfig
from ai_pycal.errors import AgreementError, ConfigFileNotFound, GitHubNotFound
from ai_pycal.github.app import GitHubApp
from ai_pycal.github.repository_api import RepositoryAPI
from ai_pycal.models import AgreementUse, PolicyChoice, Repository, RequiredAgreement

from .agreement_fetcher import AgreementFetcher

log = logging.getLogger(__name__)


class RepositorySync:
    """Bring the agreements of a repository up to date with its configuration file."""

    def __init__(self, repository: Repository, api: RepositoryAPI | None = None):
        """The synchronization of *repository*.

        Args:
            repository: The repository.
            api: The requests; those of the installation of the repository by default.
        """
        self.repository = repository
        self.api = api or RepositoryAPI(
            GitHubApp.for_installation(repository.installation.github_id)
        )

    def read_config(self) -> tuple[str, RepositoryConfig]:
        """The configuration file of the default branch.

        Returns:
            The commit and the configuration.

        Raises:
            ConfigFileNotFound: There is no file.
            ConfigFileError: The file can not be used.
        """
        name = self.repository.full_name
        commit = self.api.resolve(name, "")
        try:
            content = self.api.file(name, commit, CONFIG_PATH)
        except GitHubNotFound as error:
            raise ConfigFileNotFound(f"{CONFIG_PATH} in {name} at {commit[:7]}") from error
        home = GitHubRemote.parse(name)
        return commit, RepositoryConfig.parse(content.decode("utf-8", "replace"), home)

    def sync(self) -> list[RequiredAgreement]:
        """Read the configuration and the agreements; store them or the error.

        Returns:
            The agreements the repository asks for now.

        Raises:
            AgreementError: The configuration or an agreement can not be read. The error
                is also stored with the repository; the agreements of the last reading
                stay.
        """
        repository = self.repository
        try:
            commit, config = self.read_config()
            fetcher = AgreementFetcher(self.api)
            versions = [(spec, fetcher.fetch(spec)) for spec in config.agreements]
        except AgreementError as error:
            log.info("%s: %s %s", repository.full_name, error.code, error)
            repository.error_code = error.code
            repository.error_detail = str(error)
            repository.checked = timezone.now()
            repository.save(update_fields=["error_code", "error_detail", "checked"])
            from .project_notices import ProjectNotices

            ConfigurationRead(repository, error=error).run()
            ProjectNotices(repository).record(error)
            raise
        before = dict(repository.required_agreements.values_list("key", "version_id"))
        with transaction.atomic():
            required = []
            for position, (spec, version) in enumerate(versions):
                version.projects.add(repository)
                agreement, _ = RequiredAgreement.objects.update_or_create(
                    repository=repository,
                    key=spec.id,
                    defaults={
                        "name": spec.name,
                        "ref": spec.ref,
                        "description": spec.description,
                        "mandatory": spec.mandatory,
                        "version": version,
                        "labels": list(spec.labels),
                        "unsigned_labels": list(spec.unsigned_labels),
                        "position": position,
                    },
                )
                required.append(agreement)
                # mandatory or optional belongs to this version of the configuration
                AgreementUse.objects.update_or_create(
                    repository=repository,
                    version=version,
                    key=spec.id,
                    defaults={"mandatory": spec.mandatory},
                )
            repository.required_agreements.exclude(key__in=[s.id for s, _ in versions]).delete()
            by_key = {agreement.key: agreement for agreement in required}
            for position, spec in enumerate(config.choices):
                choice, _ = PolicyChoice.objects.update_or_create(
                    repository=repository,
                    key=spec.key,
                    defaults={
                        "name": spec.name,
                        "description": spec.description,
                        "default": spec.default,
                        "labels": list(spec.labels),
                        "position": position,
                    },
                )
                choice.agreements.set([by_key[key] for key in spec.agreements])
            repository.choices.exclude(key__in=[spec.key for spec in config.choices]).delete()
            labels = {
                label for spec in config.agreements for label in spec.labels + spec.unsigned_labels
            }
            labels.update(label for spec in config.choices for label in spec.labels)
            repository.managed_labels = sorted(set(repository.managed_labels) | labels)
            checks = {spec.id for spec in config.agreements}
            if config.choices:
                checks.add("choices/selection")
            repository.managed_checks = sorted(set(repository.managed_checks) | checks)
            repository.config_commit = commit
            repository.config_version = str(config.version)
            repository.error_code = ""
            repository.error_detail = ""
            repository.checked = timezone.now()
            repository.save()
        from .project_notices import ProjectNotices

        ConfigurationRead(repository, str(config.version), len(required)).run()
        for agreement in required:
            if agreement.key in before and before[agreement.key] != agreement.version_id:
                AgreementChanged(repository, agreement.name, agreement.version).run()
        ProjectNotices(repository).resolve_configuration()
        return required
