# elasticmodels/tests/test_settings.py
# author: andrew young
# email: ayoung@thewulf.org

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

ROOT_URLCONF = ["elasticmodels.urls"]

INSTALLED_APPS = ["elasticmodels"]

