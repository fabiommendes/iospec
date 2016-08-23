import pytest
from iospec.types import OutEllipsis


def test_simple_ellipsis_no_match():
    template = OutEllipsis('foo...bar')

    assert template != 'hamspam'
    assert template != 'hambar'
    assert template != 'foospam'
    assert template != 'foobarspam'
    assert template != 'spamfoobar'


def test_simple_ellipsis_matches():
    template = OutEllipsis('foo...bar')

    assert template == 'foobar'
    assert template == 'foospambar'


def test_multi_ellipsis_matches():
    template = OutEllipsis('foo...bar...baz')

    assert template == 'foobarbaz'
    assert template == 'foospambarbaz'
    assert template == 'foobarspambaz'
    assert template == 'foohambarspambaz'


def test_ellipsis_escapes():
    template = OutEllipsis('foo\\...bar...baz')

    assert template != 'foobarbaz'
    assert template != 'foospambarbaz'
    assert template == 'foo...barspambaz'
    assert template == 'foo...barspambaz'
