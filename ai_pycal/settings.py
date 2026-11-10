"""Settings, configured with environment variables; docs/reference/settings.rst lists them."""

# The type hints of django-environ allow no defaults; the values are checked by Django.
# pyright: reportArgumentType=false, reportReturnType=false

import os
import sys
from pathlib import Path

import environ

from ai_pycal.theme import Theme

BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env()
DATA_DIR = Path(env("DATA_DIR", default=str(BASE_DIR / "data")))
TESTING = "pytest" in sys.modules


def kept_secret(name: str) -> str:
    """A secret from the environment, or generated once into the data directory.

    Args:
        name: The name of the setting and of its file, such as ``SECRET_KEY``.

    Returns:
        The secret.
    """
    if env(name, default=""):
        return env(name)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / name.lower()
    if not path.exists():
        from django.core.management.utils import get_random_secret_key

        path.write_text(get_random_secret_key())
        path.chmod(0o600)
    return path.read_text().strip()


DEBUG = env.bool("DEBUG", default=False)
SECRET_KEY = kept_secret("SECRET_KEY")

SITE_NAME = env("SITE_NAME", default="ai.pycal.org")
# the address of the site: the links of the checks on pull requests and of the emails
SITE_URL = env("SITE_URL", default="https://ai.pycal.org").rstrip("/")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["*"])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
X_FRAME_OPTIONS = "DENY"  # nobody signs in a frame of another site

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    # before allauth: its templates in templates/ replace those of allauth
    "ai_pycal",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.github",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "ai_pycal.middleware.ErrorPageMiddleware",
]

ROOT_URLCONF = "ai_pycal.urls"
WSGI_APPLICATION = "ai_pycal.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "ai_pycal.context.site",
            ],
        },
    },
]

DATABASES = {"default": env.db("DATABASE_URL", default=f"sqlite:///{DATA_DIR / 'db.sqlite3'}")}
DATABASES["default"]["CONN_MAX_AGE"] = 60
if DATABASES["default"]["ENGINE"].endswith("sqlite3"):
    DATABASES["default"].setdefault("OPTIONS", {}).update(
        {
            "timeout": 30,
            "transaction_mode": "IMMEDIATE",
            "init_command": "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;",
        }
    )
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Sign in with GitHub only: no passwords, no email sign up.
AUTHENTICATION_BACKENDS = ["allauth.account.auth_backends.AuthenticationBackend"]
SITE_ID = 1
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/profile/"
LOGOUT_REDIRECT_URL = "/"
SOCIALACCOUNT_ONLY = True
ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_LOGIN_METHODS = {"username"}
ACCOUNT_SIGNUP_FIELDS = ["username*"]
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_LOGIN_ON_GET = False  # a button with POST: no sign in by a link of another site
SOCIALACCOUNT_STORE_TOKENS = True  # administrators: the installations they can manage
SOCIALACCOUNT_PROVIDERS = {
    "github": {
        # The GitHub App signs people in. Its tokens have no scopes: GitHub tells the
        # handle, and the installations and repositories the person may manage.
        "SCOPE": [],
        **(
            {
                "APP": {
                    "client_id": env("GITHUB_CLIENT_ID"),
                    "secret": env("GITHUB_SECRET", default=""),
                }
            }
            if env("GITHUB_CLIENT_ID", default="")
            else {}
        ),
    }
}
# GitHub handles that administer this site: the admin pages of Django
SITE_ADMINS = [login.lower() for login in env.list("SITE_ADMINS", default=[])]

# The GitHub App: docs/how-to/github-app.rst
GITHUB_API = env("GITHUB_API", default="https://api.github.com").rstrip("/")
GITHUB_APP_ID = env("GITHUB_APP_ID", default="")
GITHUB_APP_SLUG = env("GITHUB_APP_SLUG", default="")
GITHUB_APP_PRIVATE_KEY = env("GITHUB_APP_PRIVATE_KEY", default="").replace("\\n", "\n")
_key_file = env("GITHUB_APP_PRIVATE_KEY_FILE", default="")
if _key_file and not GITHUB_APP_PRIVATE_KEY and Path(_key_file).is_file():
    GITHUB_APP_PRIVATE_KEY = Path(_key_file).read_text()
GITHUB_WEBHOOK_SECRET = env("GITHUB_WEBHOOK_SECRET", default="")
# the name of the checks on the pull requests: <STATUS_CONTEXT>/<agreement>
STATUS_CONTEXT = env("STATUS_CONTEXT", default=SITE_NAME)
# seconds between showing an agreement and signing it, at least
SIGN_MIN_SECONDS = env.float("SIGN_MIN_SECONDS", default=3)
# hours a shown agreement can be signed in
SIGN_MAX_HOURS = env.float("SIGN_MAX_HOURS", default=24)

# Branding: docs/how-to/brand.rst
THEME = Theme.from_environment(dict(os.environ))
FAVICON_FILE = env("FAVICON_FILE", default="")
EXTRA_CSS_URL = env("EXTRA_CSS_URL", default="")
SOURCE_URL = env("SOURCE_URL", default="https://github.com/PyCalendar/ai.pycal.org")
DOCS_URL = env("DOCS_URL", default="https://ai-pycal-org.readthedocs.io/en/latest/")

EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_BACKEND = (
    "django.core.mail.backends.smtp.EmailBackend"
    if EMAIL_HOST
    else "django.core.mail.backends.console.EmailBackend"
)
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=EMAIL_PORT == 465)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=not EMAIL_USE_SSL)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default=f"agreements@{SITE_NAME}")

LANGUAGE_CODE = "en"
LANGUAGES = [("en", "English")]
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        if TESTING or DEBUG
        else "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO")},
    "loggers": {"httpx": {"level": "WARNING"}},  # not every request to GitHub
}
