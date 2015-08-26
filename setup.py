#!/usr/bin/env python
# setup.py
# author: andrew young
# email: ayoung@thewulf.org

import os.path
from setuptools import setup


with open(os.path.join(os.path.dirname(__file__), "README.md")) as readme:
    README = readme.read()

# allow setup.py to be run from any path
os.chdir(
    os.path.normpath(
        os.path.join(os.path.abspath(__file__), os.pardir)))

# setup
setup(
    name="django-elasticmodels",
    version="0.1",
    packages=["elasticmodels", "elasticmodels/utils", "elasticmodels/tests"],
    include_package_data=True,
    license="BSD",
    description="a friendly api for adding elasticsearch capabilities to django models.",
    long_description=README,
    author="andrew young",
    email="ayoung@thewulf.org",
    test_suite="runtests.runtests",
    install_requires=["django>=1.7", "elasticsearch>=1.6", "setuptools"],
)
