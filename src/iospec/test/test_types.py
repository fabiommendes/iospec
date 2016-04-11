import pytest
from iospec import *
from iospec.types import LinearNode
from iospec.commands import Foo


@pytest.fixture
def spec1():
     return parse_string('''foo <bar>
barfoo

ham <spam>
eggs
''')


@pytest.fixture
def spec2():
    return parse_string('''Foo<bar>
barfoo

Ham<spam>
eggs
''')

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


def test_io_transform(spec1):
    spec1.transform_strings(lambda x: x.title())
    assert spec1[0].source() == 'Foo <Bar>\nBarfoo'


def test_normalize(spec2):
    x = normalize(spec2, presentation=True)
    assert x.source() == 'foo<bar>\nbarfoo\n\nham<spam>\neggs'


def test_io_equal(spec1, spec2):
    assert isequal(spec1, spec1)
    assert isequal(spec2, spec2)
    assert not isequal(spec1, spec2)


def test_io_equal_presentation(spec1, spec2):
    assert isequal(spec1, spec2, presentation=True)

if __name__ == '__main__':
    pytest.main('test_types.py')