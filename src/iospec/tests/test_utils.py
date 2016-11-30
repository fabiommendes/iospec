from iospec.utils import *


def test_indent():
    assert indent('foo\nbar') == '    foo\n    bar'


def test_escape_html():
    assert html_escape('x>2') == 'x&gt;2'
    assert html_escape('x>2', True) == 'x&gt;2'


def test_escape_tex():
    assert tex_escape('#1') == '\\#1'
