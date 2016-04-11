import pytest
from iospec import commands


def test_parse_number():
    func = lambda x: commands.parse_number(x, int, -128, 127)

    assert func('') == (-128, 127)
    assert func('+') == (0, 127)
    assert func('-') == (-128, 0)
    assert func('++') == (1, 127)
    assert func('--') == (-128, -1)
    assert func('+10') == (0, 10)
    assert func('-10') == (-10, 0)
    assert func('10') == (-10, 10)
    assert func('10..20') == (10, 20)
    assert func('10:20') == (10, 19)


if __name__ == '__main__':
    pytest.main('test_commands.py')