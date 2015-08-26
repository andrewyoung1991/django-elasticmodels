from __future__ import absolute_import
# elasticmodels/runtests.py
# author: andrew young
# email: ayoung@thewulf.org

import os
import sys

import django
from django.test.utils import get_runner
from django.conf import settings

import test_settings


os.environ["DJANGO_SETTINGS_MODULE"] = "elasticmodels.tests.test_settings"

if not settings.configured:
    settings.configure(**test_settings.__dict__)


def runtests(*test_args):
    if django.VERSION >= (1, 7):
        django.setup()

    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=2, interactive=True)
    failures = test_runner.run_tests(["elasticmodels"])
    sys.exit(bool(failures))


if __name__ == "__main__":
    runtests()
