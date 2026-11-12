"""The trigger of the actions that are running: a webhook, a person, or a command."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps

from ai_pycal.models import LogTrigger

_current: ContextVar[LogTrigger | None] = ContextVar("log_trigger", default=None)


class Trigger:
    """Start triggers and find the one that the running actions belong to."""

    @staticmethod
    @contextmanager
    def start(kind: str, summary: str, **scope) -> Iterator[LogTrigger]:
        """Record a trigger; the actions inside the ``with`` block belong to it.

        Args:
            kind: Such as ``webhook``, ``signed``, ``update`` or ``sign-up``.
            summary: What happened, for people, such as ``Repository configuration updated``.
            **scope: ``repository``, ``pull``, ``contributor_github_id``, ``actor_login``,
                ``delivery`` and ``public`` of :class:`~ai_pycal.models.LogTrigger`.

        Yields:
            The trigger; its scope can still be changed and saved.
        """
        trigger = LogTrigger.objects.create(kind=kind, summary=summary[:300], **scope)
        token = _current.set(trigger)
        try:
            yield trigger
        finally:
            _current.reset(token)

    @staticmethod
    def current() -> LogTrigger:
        """The trigger of the running actions.

        Returns:
            The trigger of the ``with`` block of :meth:`start`; outside of one, a new trigger
            ``background`` that only the global log shows, so that no action is lost.
        """
        found = _current.get()
        if found is None:
            found = LogTrigger.objects.create(
                kind="background", summary="Work of the site", public=False
            )
        return found

    @classmethod
    def view(cls, kind: str, summary: str, public: bool = True) -> Callable:
        """A decorator of views that change something: their POST requests are triggers.

        The scope comes from the address: ``owner`` and ``repo`` are the repository,
        ``repository_id`` the repository by its id on GitHub, ``number`` the pull request;
        the person is the signed-in GitHub account.

        Args:
            kind: The kind of the trigger.
            summary: The summary, with ``{login}`` and the arguments of the address, such
                as ``@{login} chooses a policy for #{number}``.
            public: Whether the pages of the scope show it.

        Returns:
            The decorator.
        """

        def decorate(view: Callable) -> Callable:
            @wraps(view)
            def wrapped(request, *args, **kwargs):
                if request.method != "POST":
                    return view(request, *args, **kwargs)
                scope = cls.scope(request, kwargs)
                login = scope.pop("login")
                text = summary.format(login=login, **kwargs)
                with cls.start(kind, text, public=public, **scope):
                    return view(request, *args, **kwargs)

            return wrapped

        return decorate

    @staticmethod
    def scope(request, kwargs: dict) -> dict:
        """The repository, pull request and person of a request.

        Args:
            request: The request.
            kwargs: The arguments of the address.

        Returns:
            ``repository``, ``pull``, ``contributor_github_id``, ``actor_login`` and
            ``login`` (for the summary).
        """
        from ai_pycal.models import Repository
        from ai_pycal.services.identity import GitHubIdentity

        identity = GitHubIdentity.of(request.user)
        login = identity.login if identity else getattr(request.user, "username", "")
        repository = pull = None
        if kwargs.get("owner") and kwargs.get("repo"):
            repository = Repository.objects.filter(
                full_name__iexact=f"{kwargs['owner']}/{kwargs['repo']}"
            ).first()
        if kwargs.get("repository_id"):
            repository = Repository.objects.filter(github_id=kwargs["repository_id"]).first()
        if repository and kwargs.get("number"):
            pull = repository.pull_requests.filter(number=kwargs["number"]).first()
        return {
            "repository": repository,
            "pull": pull,
            "contributor_github_id": identity.github_id if identity else None,
            "actor_login": login,
            "login": login,
        }
