import io

import pytest

from iospec import parse, parse_string, IoSpecSyntaxError, Out, In, OutEllipsis


def test_open_file():
    src = 'foo<bar>'
    assert parse(io.StringIO(src)) == parse_string(src)


def test_simple_io():
    tree = parse_string('foo<bar>\nfoobar')
    case = tree[0]
    assert case[0] == Out('foo')
    assert case[1] == In('bar')
    assert case[2] == Out('foobar')


def test_simple_ellipsis():
    tree = parse_string('foo<bar>\nfoo...bar')
    case = tree[0]
    assert case[0] == Out('foo')
    assert case[1] == In('bar')
    assert case[2] == OutEllipsis('foo...bar')
    assert isinstance(case[2], OutEllipsis)
    assert case[2] == 'fooblazbar'


def test_broken_io():
    with pytest.raises(IoSpecSyntaxError):
        parse_string('foo<bar\nfoobar')


def test_multiline_with_pipes():
    tree = parse_string(
        '|foo\n'
        '|\n'
        '|bar'
    )
    assert len(tree) == 1
    assert len(tree[0]) == 1
    assert tree[0][0] == Out('foo\n\nbar')


def test_computed_input():
    tree = parse_string('foo$name(10)')
    session = tree[0]
    assert len(session) == 2
    assert session[0].type == 'output'
    assert session[1].type == 'command'
    assert session[1].name == 'name'
    assert session[1].args == '10'


def test_import_command():
    tree = parse_string(
        '@import math\n'
        '@from random import choice\n'
        '@command\n'
        'def foo(arg):'
        '    return math.sqrt(choice([1]))')
    assert tree.commands.foo.generate('') == 1


def test_use_command():
    tree = parse_string('''
@command
def foo(arg):
     return 'computed value'

foo: $foo
''')
    assert len(tree) == 1
    assert 'foo' in tree.commands
    assert tree[0, 1].data == '$foo'


def test_hanging_dollar_sign():
    testcase = parse_string(r'U$ 10.00')[0]
    assert len(testcase) == 1
    assert testcase[0] == Out('U$ 10.00')


def test_escaped_dollar_sign():
    testcase = parse_string(r'foo\$bar')[0]
    assert testcase[0] == Out('foo$bar')


def test_escaped_lt_sign():
    testcase = parse_string(r'foo\<bar')[0]
    assert testcase[0] == Out('foo<bar')
