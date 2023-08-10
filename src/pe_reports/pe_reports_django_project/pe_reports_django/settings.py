"""
Django settings for pe_reports_django project.

Generated by 'django-admin startproject' using Django 4.1.3.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.1/ref/settings/
"""

# Standard Python Libraries

import mimetypes
import os

# Python built-in
from pathlib import Path

# Third-Party Libraries
from decouple import config
from django.contrib.messages import constants as messages

mimetypes.add_type("text/css", ".css", True)
mimetypes.add_type("text/html", ".html", True)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["127.0.0.1"]

MESSAGE_TAGS = {
    messages.DEBUG: "alert-secondary",
    messages.INFO: "alert-info",
    messages.SUCCESS: "alert-success",
    messages.WARNING: "alert-warning",
    messages.ERROR: "alert-danger",
}


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "dataAPI.apps.DataapiConfig",
    "bulkupload.apps.BulkuploadConfig",
    "home.apps.HomeConfig",
    "manage_login.apps.ManageLoginConfig",
    "report_gen.apps.ReportGenConfig",
    "stakeholder_lite.apps.StakeholderLiteConfig",
    "crispy_forms",
    "crispy_bootstrap5",
    "whitenoise.runserver_nostatic",
    "elasticapm.contrib.django",
]

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"

CRISPY_TEMPLATE_PACK = "bootstrap5"

# When adding more applicaitons be sure to add the new application to the loggers section.

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname}"
            " {asctime}"
            " {name}"
            " {funcName}"
            " {process:d}"
            " {thread:d}"
            " {message}",
            "datefmt": "%Y-%m-%d %I:%M:%S",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "maxBytes": 1024 * 1024 * 15,
            "backupCount": 10,
            "filename": "./pe_reportsLogFile.log",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "home.views": {
            "handlers": ["file"],
            "level": "INFO",
            "propagate": True,
        },
        "dataAPI.views": {
            "handlers": ["file"],
            "level": "INFO",
            "propagate": True,
        },
        "stakeholder_lite.views": {
            "handlers": ["file"],
            "level": "INFO",
            "propagate": True,
        },
        "report_gen.views": {
            "handlers": ["file"],
            "level": "INFO",
            "propagate": True,
        },
        "bulkupload.views": {
            "handlers": ["file"],
            "level": "INFO",
            "propagate": True,
        },
        "celery": {
            "handlers": ["file"],
            "level": "INFO",
            "propagate": True,
        },
        "celery.task": {
            "handlers": ["file"],
            "level": "INFO",
            "propagate": True,
        },
        "celery.worker": {
            "handlers": ["file"],
            "level": "INFO",
            "propagate": True,
        },
    },
}

ELASTIC_APM = {
  'SERVICE_NAME': 'my-service-name',

  'SECRET_TOKEN': '',

  'SERVER_URL': 'http://10.0.2.109:8200',

  'ENVIRONMENT': 'my-environment',
}



MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "elastic.contrib.django.middleware.TracingMiddleware",
]

ROOT_URLCONF = "pe_reports_django.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "pe_reports_django.wsgi.application"


# Database
# https://docs.djangoproject.com/en/4.1/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": config("database"),
        "USER": config("user"),
        "PASSWORD": config("password"),
        "HOST": config("host"),
        "PORT": config("port"),
    }
}

# Celery settings
CELERY_BROKER_URL = (
    f"amqp://{config('RABBITMQ_USER')}:{config('RABBITMQ_PASS')}@localhost:5672/"
)
CELERY_RESULT_BACKEND = "redis://localhost:6379"
CELERY_RESULT_EXPIRES = 3600


# Password validation
# https://docs.djangoproject.com/en/4.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# settings.py
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "your_smtp_server.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = "your_email@example.com"
EMAIL_HOST_PASSWORD = "your_email_password"
DEFAULT_FROM_EMAIL = "webmaster@example.com"


LOGIN_URL = "/login/"
LOGOUT_REDIRECT_URL = "/"
DJANGO_SETTINGS_MODULE = "pe_reports_django.settings"


# Internationalization
# https://docs.djangoproject.com/en/4.1/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "America/Chicago"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.1/howto/static-files/

STATIC_URL = "static/"
STATICFILES_DIRS = [
    BASE_DIR / "static",
]
# STATICFILES_DIRS = (os.path.join(BASE_DIR, 'staticfiles'),)
# print(STATIC_URL)
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"
STATIC_FINDERS = (
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
)


# Default primary key field type
# https://docs.djangoproject.com/en/4.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"


MOUNT_DJANGO_APP = True

PROJECT_NAME = "Posture and Exposure Data API"
