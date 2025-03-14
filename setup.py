#!python

import os.path
import sys

from setuptools import setup
from setuptools.command.test import test as TestCommand

try:
    import pytest
except ImportError:
    pytest = None

sys.path.insert(0, os.path.abspath("src"))
from whoosh import versionstring


class PyTest(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        # import here, cause outside the eggs aren't loaded
        import pytest

        pytest.main(self.test_args)


setup(
    version=versionstring(),
    cmdclass={"test": PyTest},
)
