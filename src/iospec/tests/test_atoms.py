import pytest

from iospec import In, Out, parse
from iospec.commands.all import Foo
from iospec.datatypes import OutEllipsis

from .test_iospec import spec1, spec2


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


class TestAtom:
    def test_equality(self):
        for cls in [In, Out]:
            assert cls('foo') == cls('foo')
            assert cls('foo') == 'foo'
            assert cls('foo') != cls('bar')
        assert In('foo') != Out('foo')


class TestExpansion:
    def test_expand_inputs(self):
        tree = parse(
            '@command\n'
            'def foo(*args):\n'
            '   return "bar"\n'
            '\n'
            'foo: $foo'
        )
        tree.expand_inputs()
        assert tree[0][1] == 'bar'

    def test_expand_and_create_inputs(self):
        tree = parse('\n\n'.join([
            'foo: <bar>',
            'foo: $foo',
            'foo: $foo(2)'
        ]), commands={'foo': Foo()})

        tree.expand_inputs(5)
        assert len(tree) == 5
        assert tree[0, 1] == 'bar'
        assert tree[1, 1] == 'foo'
        assert tree[2, 1] == 'foo'
        assert tree[3, 1] == 'foofoo'
        assert tree[4, 1] == 'foofoo'

    def test_io_transform(self, spec1):
        spec1.transform_strings(lambda x: x.title())
        assert spec1[0].source() == 'Foo <Bar>\nBarfoo'

    def test_normalize(self, spec2):
        spec2.normalize()
        spec2.casefold()
        spec2.skip_spaces()
        assert spec2.source() == 'foo<bar>\nbarfoo\n\nham<spam>\neggs'