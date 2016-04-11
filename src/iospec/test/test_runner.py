#
# Tests random input generators and runners
#
import io
import pytest
from iospec.types import Out, In
from iospec.runners import IoObserver


def test_io_observer():
    io_obs = IoObserver(['Ringo'])

    namespace = {
        'print': io_obs.print,
        'input': io_obs.input,
    }

    exec(
        "name = input('Name? ')\n"
        "print('Hi %s!' % name)",
    namespace)

    assert io_obs.flush() == [Out('Name? '), In('Ringo'), Out('Hi Ringo!')]

if __name__ == '__main__':
    pytest.main('test_runner.py')