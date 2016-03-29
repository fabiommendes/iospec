import io
import pytest
from iospec import parse, parse_string


def test_open_file():
    src = 'foo<bar>'
    assert parse(io.StringIO(src)) == parse_string(src)


def test_simple_io():
    tree = parse_string('foo<bar>\nfoobar')
    case = tree[0]
    assert case[0] == 'foo'
    assert case[1] == 'bar'
    assert case[2] == 'foobar'


def test_multiline_with_pipes():
    tree = parse_string(
        '|foo\n'
        '|\n'
        '|bar'
    )
    assert len(tree) == 1
    assert len(tree[0]) == 1
    assert tree[0][0] == 'foo\n\nbar'


def test_computed_input():
    tree = parse_string('foo$name(10)')
    session = tree[0]
    assert len(session) == 2
    assert session[0].type == 'output'
    assert session[1].type == 'input-command'
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


if __name__ == '__main__':
    pytest.main('test_parser.py')

