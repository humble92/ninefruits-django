"""Settings shared by every environment. Values come from the environment (.env) only."""

from pathlib import Path

import environ

from ninefruits.core.pool import reset_connection

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env", overwrite=False)

DJANGO_ENV = env.str("DJANGO_ENV", default="local")
SECRET_KEY = env.str("DJANGO_SECRET_KEY")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])
APP_URL = env.str("APP_URL", default="http://localhost:8000")
APP_NAME = env.str("APP_NAME", default="Ninefruits")

NINEFRUITS_APPS = [
    "ninefruits.core",
    "ninefruits.i18n",
    "ninefruits.settings",
    "ninefruits.security",
    "ninefruits.audit",
    "ninefruits.pii",
    "ninefruits.media",
    "ninefruits.pdf",
    "ninefruits.institution",
    "ninefruits.organization",
    "ninefruits.facility",
    "ninefruits.term",
    "ninefruits.person",
    "ninefruits.admission",
    "ninefruits.curriculum",
    "ninefruits.offering",
    "ninefruits.registration",
    "ninefruits.grading",
    "ninefruits.evaluation",
    "ninefruits.certificate",
    "ninefruits.assessment",
    "ninefruits.attendance",
    "ninefruits.graduation",
    "ninefruits.reporting",
    "ninefruits.lms",
    "ninefruits.importing",
    "ninefruits.setup",
    "ninefruits.adminpanel",
    "ninefruits.portal",
    "ninefruits.api",
]

INSTALLED_APPS = [
    # unfold must come before the admin. BasicAppConfig: unfold must not replace the default
    # admin site; NinefruitsAdminConfig sets it to ninefruits.adminpanel.sites.NinefruitsAdminSite.
    "unfold.apps.BasicAppConfig",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "unfold.contrib.import_export",
    "ninefruits.adminpanel.apps.NinefruitsAdminConfig",
    # Before django.contrib.auth so its createsuperuser (disabled) replaces auth's.
    "ninefruits.adminpanel",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "allauth",
    "allauth.account",
    "allauth.mfa",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.openid_connect",
    "rest_framework",
    "knox",
    "drf_spectacular",
    "django_filters",
    "django_celery_beat",
    "import_export",
    "django_vite",
    *(app for app in NINEFRUITS_APPS if app != "ninefruits.adminpanel"),
]

MIDDLEWARE = [
    # Order (porting-plan 9): request context -> session -> auth -> locale -> database session
    # context -> active account -> two-factor policy.
    "django.middleware.security.SecurityMiddleware",
    "ninefruits.core.middleware.AssignRequestContextMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # Before the security middleware: they add flash messages (deactivated account, MFA).
    "django.contrib.messages.middleware.MessageMiddleware",
    "ninefruits.i18n.middleware.SetLocaleMiddleware",
    "ninefruits.adminpanel.middleware.AdminTimezoneMiddleware",
    "ninefruits.core.middleware.SetDatabaseSessionContextMiddleware",
    "ninefruits.security.middleware.EnsureUserIsActiveMiddleware",
    "ninefruits.security.middleware.EnforceMfaPolicyMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.csp.ContentSecurityPolicyMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.template.context_processors.i18n",
                "django.template.context_processors.csp",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "ninefruits.portal.context_processors.site",
            ],
        },
    },
]

# --- Database (porting-plan 5.3) -------------------------------------------------------------
# default: app_runtime (row level security applies, no DDL). migrator: app_migrator (schema
# owner). Only the migrate wrapper and test database setup use the migrator connection.
DB_RUNTIME_ROLE = env.str("DB_RUNTIME_ROLE", default="app_runtime")
DB_REPORTING_ROLE = env.str("DB_REPORTING_ROLE", default="app_reporting")
_DB_POOL = env.bool("DB_POOL", default=False)
_db_common = {
    "ENGINE": "django.db.backends.postgresql",
    "HOST": env.str("DB_HOST", default="127.0.0.1"),
    "PORT": env.str("DB_PORT", default="5432"),
    "NAME": env.str("DB_DATABASE", default="ninefruits"),
    "CONN_MAX_AGE": 0,
    "TEST": {"NAME": env.str("DB_TEST_DATABASE", default="test_ninefruits")},
}
DATABASES = {
    "default": {
        **_db_common,
        "USER": env.str("DB_USERNAME", default=DB_RUNTIME_ROLE),
        "PASSWORD": env.str("DB_PASSWORD", default=""),
        "OPTIONS": {
            "pool": {
                "min_size": env.int("DB_POOL_MIN", default=2),
                "max_size": env.int("DB_POOL_MAX", default=20),
                "reset": reset_connection,
            }
        }
        if _DB_POOL
        else {},
    },
    "migrator": {
        **_db_common,
        "USER": env.str("DB_MIGRATOR_USERNAME", default="app_migrator"),
        "PASSWORD": env.str("DB_MIGRATOR_PASSWORD", default=""),
    },
}
# Superuser credentials are only needed to create databases (tests, setup scripts).
DB_SUPERUSER_USERNAME = env.str("DB_SUPERUSER_USERNAME", default="postgres")
DB_SUPERUSER_PASSWORD = env.str("DB_SUPERUSER_PASSWORD", default="")
# Ninefruits apps set BigAutoField in their AppConfig; third-party apps keep their own default.
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

# --- Authentication (porting-plan 7) ---------------------------------------------------------
AUTH_USER_MODEL = "security.User"
AUTHENTICATION_BACKENDS = [
    "ninefruits.security.backends.CatalogPermissionBackend",
    # Email or student number + password (lockout, same failure for every reason).
    "ninefruits.security.backends.LoginIdentifierBackend",
]
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]
LOGIN_URL = "account_login"
LOGIN_REDIRECT_URL = "portal:dashboard"

ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
# Signing in does not need a verified address (only applying does, Phase 3), as in the original.
ACCOUNT_EMAIL_VERIFICATION = "optional"
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_ADAPTER = "ninefruits.security.adapters.AccountAdapter"
SOCIALACCOUNT_ADAPTER = "ninefruits.security.adapters.SocialAccountAdapter"
ACCOUNT_LOGIN_ON_PASSWORD_RESET = False
ACCOUNT_LOGOUT_ON_PASSWORD_CHANGE = False
# Original "login" limiter: 5 per minute per account (or sign-in name) and IP address.
ACCOUNT_RATE_LIMITS = {"login_failed": "5/m/key"}
ACCOUNT_FORMS = {
    "login": "ninefruits.security.forms.LoginForm",
    # Applicant self registration (RegisterApplicant, Phase 3).
    "signup": "ninefruits.admission.forms.ApplicantSignupForm",
}
# Original auth.password_timeout: a password confirmation lasts three hours.
ACCOUNT_REAUTHENTICATION_TIMEOUT = env.int("AUTH_PASSWORD_TIMEOUT", default=10800)
MFA_ADAPTER = "ninefruits.security.adapters.MfaAdapter"
MFA_SUPPORTED_TYPES = ["totp", "recovery_codes"]
# "Remember this device" is ninefruits.security.services.trusted_devices (duration from the
# security settings, bound to the enrollment), not allauth's trust stage.
MFA_TRUST_ENABLED = False

# --- Internationalization (porting-plan 6) ---------------------------------------------------
LANGUAGE_CODE = "en"
LANGUAGES = [
    ("en", "English"),
    ("ko", "한국어"),
    ("zh-hans", "简体中文"),
    ("lo", "ລາວ"),
]
FALLBACK_LANGUAGE = "en"
LOCALE_PATHS = [BASE_DIR / "locale"]
USE_I18N = True
USE_TZ = True
TIME_ZONE = env.str("APP_TIMEZONE", default="UTC")
# Initial value of the institution settings time zone (settings migration only).
INSTITUTION_TIMEZONE = env.str("INSTITUTION_TIMEZONE", default="UTC")
# Date/number formats for languages Django does not ship (lo).
FORMAT_MODULE_PATH = ["ninefruits.i18n.formats"]

# --- Static files and assets ------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
DJANGO_VITE = {
    "default": {
        "dev_mode": env.bool("VITE_DEV_MODE", default=False),
        "manifest_path": BASE_DIR / "static" / "dist" / "manifest.json",
        "static_url_prefix": "dist",
    }
}

# Private files are never served directly; downloads go through permission checked views.
PRIVATE_MEDIA_ROOT = Path(env.str("PRIVATE_MEDIA_ROOT", default=str(BASE_DIR / "storage" / "private")))
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage", "OPTIONS": {"location": PRIVATE_MEDIA_ROOT}},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

# --- Cache, sessions, queue ------------------------------------------------------------------
REDIS_URL = env.str("REDIS_URL", default="redis://127.0.0.1:6379/0")
CACHES = {"default": {"BACKEND": "django_redis.cache.RedisCache", "LOCATION": REDIS_URL}}
SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"
SESSION_COOKIE_AGE = env.int("SESSION_LIFETIME_MINUTES", default=120) * 60
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

CELERY_BROKER_URL = env.str("CELERY_BROKER_URL", default=REDIS_URL)
CELERY_RESULT_BACKEND = env.str("CELERY_RESULT_BACKEND", default=REDIS_URL)
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=False)
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_TASK_ACKS_LATE = True
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
CELERY_TIMEZONE = TIME_ZONE

# --- Mail (Django 6.1 MAILERS) ---------------------------------------------------------------
MAILERS = {
    "default": {
        "BACKEND": env.str("MAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend"),
        "OPTIONS": {"host": env.str("MAIL_HOST", default="127.0.0.1"), "port": env.int("MAIL_PORT", default=1025)},
    }
}
DEFAULT_FROM_EMAIL = env.str("DEFAULT_FROM_EMAIL", default="no-reply@ninefruits.test")

# --- PII (porting-plan 10, 11) ----------------------------------------------------------------
PII_ENCRYPTION_KEY = env.str("PII_ENCRYPTION_KEY", default="")
PII_PREVIOUS_KEYS = env.list("PII_PREVIOUS_KEYS", default=[])
PII_HASH_KEY = env.str("PII_HASH_KEY", default="")

# --- PDF -------------------------------------------------------------------------------------
GOTENBERG_URL = env.str("GOTENBERG_URL", default="http://127.0.0.1:3000")
GOTENBERG_TIMEOUT = env.int("GOTENBERG_TIMEOUT", default=60)

# --- REST framework (porting-plan 12) --------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "knox.auth.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {"anon": "30/min", "user": "120/min", "integration": "600/min"},
}
SPECTACULAR_SETTINGS = {"TITLE": "Ninefruits API", "VERSION": "1.0.0", "SERVE_INCLUDE_SCHEMA": False}

# --- Security headers (porting-plan 11) ------------------------------------------------------
from django.utils.csp import CSP  # noqa: E402

SECURE_CSP = {
    "default-src": [CSP.SELF],
    "script-src": [CSP.SELF, CSP.NONCE],
    "style-src": [CSP.SELF, CSP.UNSAFE_INLINE],
    "img-src": [CSP.SELF, "data:"],
    "frame-ancestors": [CSP.NONE],
}
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

# --- Logging ---------------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"json": {"()": "ninefruits.core.logging.JsonFormatter"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "json"}},
    "root": {"handlers": ["console"], "level": env.str("LOG_LEVEL", default="INFO")},
}

# Admin panel (porting-plan 5.1, original AdminPanelProvider). Callables live in
# ninefruits.adminpanel.config; the sidebar is built per request from the registered admins.
UNFOLD = {
    "SITE_TITLE": "ninefruits.adminpanel.config.site_title",
    "SITE_HEADER": "ninefruits.adminpanel.config.site_title",
    "SITE_URL": "/portal/",
    "SITE_SYMBOL": "school",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": False,
    "SHOW_LANGUAGES": True,
    # Language menu: the institution's supported locales, posted to the locale switcher.
    "LANGUAGES": {
        "navigation": "ninefruits.i18n.admin_languages.language_navigation",
        "action": "ninefruits.i18n.admin_languages.language_action",
    },
    "ENVIRONMENT": "ninefruits.adminpanel.config.environment",
    "DASHBOARD_CALLBACK": "ninefruits.adminpanel.config.dashboard",
    "COLORS": {"primary": "ninefruits.adminpanel.config.primary_colors"},
    "ACCOUNT": {"navigation": "ninefruits.adminpanel.config.account_links"},
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": "ninefruits.adminpanel.navigation.sidebar_navigation",
    },
}
