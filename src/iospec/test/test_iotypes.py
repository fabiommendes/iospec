import io
import pytest
from iospec.iotypes import *
from iospec import parse_string
from iospec.commands import Foo


def test_atom_equality():
    for cls in [In, Out]:
        assert cls('foo') == cls('foo')
        assert cls('foo') == 'foo'
        assert cls('foo') != cls('bar')
    assert In('foo') != Out('foo')


def test_node_equality():
    assert LinearNode([In('foo')]) == LinearNode([In('foo')])
    assert IoSpec() == IoSpec()


def test_expand_inputs():
    tree = parse_string("""
@command
def foo(*args):
    return 'bar'

foo: $foo
""")
    tree.expand_inputs()
    assert tree[0][1] == 'bar'


def test_expand_and_create_inputs():
    tree = parse_string("""foo: <bar>

    foo: $foo

    foo: $foo(2)
""", commands={'foo': Foo()})
    tree.expand_inputs(5)
    assert len(tree) == 5
    assert tree[0, 1] == 'bar'
    assert tree[1, 1] == 'foo'
    assert tree[2, 1] == 'foo'
    assert tree[3, 1] == 'foofoo'
    assert tree[4, 1] == 'foofoo'


if __name__ == '__main__':
    pytest.main('test_iotypes.py')