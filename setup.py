#!python

import os.path
import sys

from setuptools import setup

sys.path.insert(0, os.path.abspath("src"))
from whoosh import versionstring

setup(
    version=versionstring(),
)
