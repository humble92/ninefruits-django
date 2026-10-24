from .base import *  # noqa: F403
from .base import DATABASES, DJANGO_VITE, env

DJANGO_ENV = "testing"
DEBUG = False
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
MAILERS = {"default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}}
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
SESSION_ENGINE = "django.contrib.sessions.backends.db"
DATABASES["default"]["OPTIONS"] = {}
GOTENBERG_URL = env.str("GOTENBERG_URL", default="http://127.0.0.1:3000")
PII_ENCRYPTION_KEY = env.str("PII_ENCRYPTION_KEY", default="base64:dGVzdC1waWktZW5jcnlwdGlvbi1rZXktMzJieXRlcyE=")
PII_HASH_KEY = env.str("PII_HASH_KEY", default="base64:dGVzdC1waWktaGFzaC1rZXktMzItYnl0ZXMtbG9uZyE=")
RATELIMIT_ENABLE = True
ACCOUNT_RATE_LIMITS = False
# Templates render without a Vite build (no static/dist/manifest.json needed): dev mode only
# emits <script src="http://localhost:5173/...">.
DJANGO_VITE = {"default": {**DJANGO_VITE["default"], "dev_mode": True}}
