"""Isolated test configuration; never points at the development database."""

import os

from .development import *  # noqa: F403

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
SECRET_KEY = "test-only-secret-key-long-enough-for-hs256-verification"
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]

# Opt in to PostgreSQL for transaction/concurrency tests. No environment
# variables means a disposable in-memory SQLite database for functional tests.
if not os.environ.get("POSTGRES_DB"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        },
    }
