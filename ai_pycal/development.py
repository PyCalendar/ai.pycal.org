"""Run development commands with defaults applied after uv loads .env."""

import argparse
import os
from collections.abc import MutableMapping
from urllib.parse import urlsplit


def configure_environment(
    environment: MutableMapping[str, str], port: int = 5000, docs_port: int = 8000
) -> None:
    """Fill missing development settings without replacing configured values.

    Args:
        environment: The process environment, after any dotenv file was loaded.
        port: The local application port.
        docs_port: The port served by make livehtml.
    """
    defaults = {
        "DEBUG": "1",
        "SITE_URL": f"http://localhost:{port}",
        "DOCS_URL": f"http://localhost:{docs_port}/",
        "DJANGO_SETTINGS_MODULE": "ai_pycal.settings",
    }
    for name, default in defaults.items():
        if not environment.get(name):
            environment[name] = default
    site_url = environment["SITE_URL"].rstrip("/")
    host = urlsplit(site_url).hostname or "localhost"
    allowed_host = f"[{host}]" if ":" in host else host
    defaults = {
        "SITE_NAME": host,
        "ALLOWED_HOSTS": ",".join(dict.fromkeys([allowed_host, "localhost", "127.0.0.1", "[::1]"])),
        "CSRF_TRUSTED_ORIGINS": site_url,
    }
    for name, default in defaults.items():
        if not environment.get(name):
            environment[name] = default


def main(argv: list[str] | None = None) -> None:
    """Apply local defaults before Django reads settings and execute a command.

    Args:
        argv: Development options followed by a Django management command.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--docs-port", type=int, default=8000)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    options = parser.parse_args(argv)
    if not options.command:
        parser.error("a Django management command is required")
    configure_environment(os.environ, options.port, options.docs_port)
    from django.core.management import execute_from_command_line

    execute_from_command_line(["manage.py", *options.command])


if __name__ == "__main__":
    main()
