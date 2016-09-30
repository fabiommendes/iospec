import pytest
import iospec


def test_project_defines_author_and_version():
    assert hasattr(iospec, '__author__')
    assert hasattr(iospec, '__version__')
