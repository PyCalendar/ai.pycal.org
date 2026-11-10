"""The translation table: any exception becomes an error people understand."""

import httpx

from .base import AgreementError, UnexpectedError
from .github import GitHubError, GitHubUnreachable


def all_errors() -> dict[str, type[AgreementError]]:
    """Every error class by its name.

    Returns:
        The classes by their names.

    Examples:
        >>> "ConfigFileNotFound" in all_errors()
        True
    """
    found, todo = {}, [AgreementError]
    while todo:
        cls = todo.pop()
        found[cls.__name__] = cls
        todo.extend(cls.__subclasses__())
    return found


def by_code(code: str) -> type[AgreementError] | None:
    """The class of an error by its name, as stored with repositories; None if unknown.

    Args:
        code: The name of the class.

    Returns:
        The class.

    Examples:
        >>> by_code("NoAgreements").__name__
        'NoAgreements'
        >>> by_code("NoSuchError") is None
        True
    """
    return all_errors().get(code or "")


def translate(error: BaseException) -> AgreementError:
    """The error to show for any exception.

    Args:
        error: Any exception.

    Returns:
        The same error, the one it means, or ``UnexpectedError``.
    """
    if isinstance(error, AgreementError):
        return error
    if isinstance(error, httpx.TransportError):
        return GitHubUnreachable(str(error))
    if isinstance(error, httpx.HTTPError):
        return GitHubError(str(error))
    return UnexpectedError(f"{type(error).__name__}: {error}")
