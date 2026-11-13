"""The public information of the pages as data, for their JSON at ``<page>.json``.

Each function turns what a page shows into lists and mappings: only what a visitor who is
not signed in sees. Addresses on the site are paths, such as ``/project/owner/name/``; each
object of a page has ``page`` and ``json``, the address of its page and of its JSON.
"""

from django.urls import reverse

from ai_pycal.services.pull_state import PullState


def json_address(page: str) -> str:
    """The address of the JSON of a page.

    Args:
        page: The path of the page, ending with ``/``.

    Returns:
        The path of its JSON.

    Examples:
        >>> json_address("/project/PyCalendar/icalendar/")
        '/project/PyCalendar/icalendar.json'
        >>> json_address("/")
        '/index.json'
    """
    return "/index.json" if page == "/" else page.rstrip("/") + ".json"


def page_address(json_path: str) -> str:
    """The address of the page of a JSON address; the reverse of :func:`json_address`.

    Args:
        json_path: The path, ending with ``.json``.

    Returns:
        The path of the page.

    Examples:
        >>> page_address("/project/PyCalendar/icalendar.json")
        '/project/PyCalendar/icalendar/'
        >>> page_address("/index.json")
        '/'
    """
    return "/" if json_path == "/index.json" else json_path.removesuffix(".json") + "/"


def links(page: str) -> dict:
    """The addresses of a page and of its JSON.

    Args:
        page: The path of the page.

    Returns:
        ``page`` and ``json``.
    """
    return {"page": page, "json": json_address(page)}


def error(error_class, detail: str = "") -> dict | None:
    """An error of the site with its documentation.

    Args:
        error_class: The class of the error, or None.
        detail: What exactly happened.

    Returns:
        ``code``, ``title``, ``detail`` and ``documentation``; None without an error.
    """
    if error_class is None:
        return None
    return {
        "code": error_class.__name__,
        "title": str(error_class.title),
        "detail": detail,
        "documentation": error_class.docs_url(),
    }


def project(repository) -> dict:
    """A project of the site.

    Args:
        repository: The repository.

    Returns:
        Its name, owner and addresses.
    """
    return {
        "full_name": repository.full_name,
        "owner": repository.owner,
        "name": repository.name,
        "github": repository.url,
        **links(f"/project/{repository.full_name}/"),
    }


def contributor(login: str) -> dict:
    """A person, by their GitHub handle.

    Args:
        login: The handle.

    Returns:
        The handle and the addresses of their page.
    """
    return {"login": login, **links(reverse("contributor", args=[login]))}


def version(found) -> dict:
    """A version of an agreement: a file at the commit that last changed it.

    Args:
        found: The :class:`~ai_pycal.models.AgreementVersion`.

    Returns:
        Its title, source, path, commit and addresses.
    """
    return {
        "id": found.pk,
        "title": found.title,
        "source": found.source,
        "path": found.path,
        "commit": found.commit,
        "committed": found.committed,
        "github": found.url,
        **links(reverse("agreement", args=[found.pk])),
    }


def agreement(required) -> dict:
    """An agreement as a project asks for it.

    Args:
        required: The :class:`~ai_pycal.models.RequiredAgreement`.

    Returns:
        Its key, name, labels and version.
    """
    return {
        "key": required.key,
        "name": required.name,
        "title": required.title,
        "description": required.description,
        "mandatory": required.mandatory,
        "ref": required.ref,
        "labels": list(required.labels),
        "unsigned_labels": list(required.unsigned_labels),
        "reading_seconds": required.reading_seconds,
        "version": version(required.version),
    }


def choice(found) -> dict:
    """A choice of a project, such as whether AI helped.

    Args:
        found: The :class:`~ai_pycal.models.PolicyChoice`.

    Returns:
        Its key, name, labels and the keys of its agreements.
    """
    return {
        "key": found.key,
        "name": found.name,
        "description": found.description,
        "default": found.default,
        "labels": list(found.labels),
        "agreements": [required.key for required in found.agreements.all()],
    }


def pull(found) -> dict:
    """A pull request and its state.

    Args:
        found: The :class:`~ai_pycal.models.PullRequest`.

    Returns:
        Its number, title, author, state, choice and addresses.
    """
    state = getattr(found, "state", None) or PullState.of(found)
    return {
        "number": found.number,
        "title": found.title,
        "project": found.repository.full_name,
        "author": contributor(found.author_login),
        "state": state,
        "open": found.open,
        "merged": found.merged,
        "choice": found.choice.key if found.choice else None,
        "github": found.url,
        **links(f"/project/{found.repository.full_name}/pulls/{found.number}/"),
    }


def signature(found) -> dict:
    """A signature: who signed and when.

    Args:
        found: The :class:`~ai_pycal.models.Signature`.

    Returns:
        The person and the time.
    """
    return {"contributor": contributor(found.login), "signed": found.signed}


def trigger(found) -> dict:
    """An entry of a log: what happened and the actions that followed.

    Args:
        found: The :class:`~ai_pycal.models.LogTrigger`, with ``shown``: its actions that
            the log shows.

    Returns:
        Its kind, summary, time, who caused it and its actions.
    """
    return {
        "id": found.pk,
        "kind": found.kind,
        "summary": found.summary,
        "created": found.created,
        "actor": found.actor_login or None,
        "actions": [
            {"kind": action.kind, "text": action.text, "created": action.created}
            for action in getattr(found, "shown", [])
        ],
    }
