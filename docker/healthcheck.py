"""The health check of the container: GET /health/ with a host of ALLOWED_HOSTS."""

import os
import sys
import urllib.request

LOCAL = "127.0.0.1"


def allowed_host(allowed_hosts: str) -> str:
    """The first host name of ALLOWED_HOSTS, to send as Host.

    Args:
        allowed_hosts: The value of ALLOWED_HOSTS, comma separated.

    Returns:
        The host; for ``*`` or nothing, 127.0.0.1.

    Examples:
        >>> allowed_host("sign.pycal.org,www.sign.pycal.org")
        'sign.pycal.org'
        >>> allowed_host("*")
        '127.0.0.1'
    """
    for host in allowed_hosts.split(","):
        host = host.strip().lstrip(".")
        if host and "*" not in host:
            return host
    return LOCAL


def check(port: str, allowed_hosts: str, timeout: float = 8) -> bool:
    """Whether the site in this container answers its health check.

    Args:
        port: The port of nginx in the container.
        allowed_hosts: The value of ALLOWED_HOSTS.
        timeout: Seconds to wait for the answer.

    Returns:
        True if the database answers.
    """
    request = urllib.request.Request(
        f"http://{LOCAL}:{port}/health/", headers={"Host": allowed_host(allowed_hosts)}
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status == 200
    except OSError as error:
        print(f"unhealthy: {error}", file=sys.stderr)
        return False


if __name__ == "__main__":
    sys.exit(0 if check(os.environ["PORT"], os.environ.get("ALLOWED_HOSTS", "")) else 1)
