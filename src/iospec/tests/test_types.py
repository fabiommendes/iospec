import json
from numbers import Number

import pytest

import iospec
from iospec import IoSpec, In, Out, parse, normalize, isequal
from iospec.commands.all import Foo
from iospec.types import LinearNode


@pytest.fixture
def spec1():
    return parse('''foo <bar>
barfoo

ham <spam>
eggs
''')


@pytest.fixture
def spec2():
    return parse('''Foo<bar>
barfoo

Ham<spam>
eggs
''')


class TestAtom:
    def test_equality(self):
        for cls in [In, Out]:
            assert cls('foo') == cls('foo')
            assert cls('foo') == 'foo'
            assert cls('foo') != cls('bar')
        assert In('foo') != Out('foo')


def test_node_equality():
    assert LinearNode([In('foo')]) == LinearNode([In('foo')])
    assert IoSpec() == IoSpec()


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
        x = normalize(spec2, presentation=True)
        assert x.source() == 'foo<bar>\nbarfoo\n\nham<spam>\neggs'


class TestIsEqualFunction:
    def test_io_equal(self, spec1, spec2):
        assert isequal(spec1, spec1)
        assert isequal(spec2, spec2)
        assert not isequal(spec1, spec2)

    def test_io_equal_presentation(self, spec1, spec2):
        assert isequal(spec1, spec2, presentation=True)


class AbstractTestCase:
    base_cls = None
    base_args = ()
    base_type = None
    base_json = {}

    @pytest.fixture
    def cls(self):
        return self.base_cls

    @pytest.fixture
    def obj(self):
        return self.base_cls(*self.base_args)

    def test_has_type(self, obj):
        assert obj.type == self.base_type

    def test_has_a_default_priority(self, obj):
        assert isinstance(obj.priority, Number)

    def test_can_override_priority(self, obj):
        obj.priority = 42
        assert obj.priority == 42

    def test_object_is_simple(self, obj):
        assert not obj.is_simple

    def test_object_is_expanded(self, obj):
        assert not obj.is_expanded

    def test_object_is_input(self, obj):
        assert not obj.is_input

    def test_object_is_error(self, obj):
        assert not obj.is_error

    def test_object_has_valid_json_representation(self, obj):
        json_data = obj.to_json()

        # Assert it is expected object
        assert json_data['type'] == self.base_type
        assert self.base_json == json_data
        self.assert_valid_json(json_data)

    def test_object_can_be_created_from_json_repr(self, cls, obj):
        json = obj.to_json()
        new = cls.from_json(json)
        assert json == new.to_json()
        assert new == obj

    def assert_valid_json(self, data):
        dump = json.dumps(data)
        reconstructed = json.loads(dump)
        assert reconstructed == data


class TestSimpleTestCase(AbstractTestCase):
    base_cls = iospec.SimpleTestCase
    base_args = ([Out('foo'), In('bar')],)
    base_type = 'simple'
    base_json = {'type': 'simple', 'data': [['Out', 'foo'], ['In', 'bar']]}

    def test_object_is_simple(self, obj):
        assert obj.is_simple

    def test_object_is_expanded(self, obj):
        assert obj.is_expanded


class TestInputTestCase(AbstractTestCase):
    base_cls = iospec.InputTestCase
    base_args = (['foo', 'bar'],)
    base_type = 'input'
    base_json = {'type': 'input', 'data': [['In', 'foo'], ['In', 'bar']]}

    def test_object_is_input(self, obj):
        assert obj.is_input


class TestErrorTestCase(AbstractTestCase):
    base_cls = iospec.ErrorTestCase
    base_args = TestSimpleTestCase.base_args
    base_type = 'error'
    base_json = dict(TestSimpleTestCase.base_json,
                     type='error', error_type='runtime', error_message='error')

    @pytest.fixture
    def obj(self, cls):
        return cls(*self.base_args, error_type='runtime', error_message='error')

    @pytest.fixture
    def runtime(self, obj):
        return obj

    @pytest.fixture
    def build(self, cls):
        return cls(error_type='build', error_message='build error')

    @pytest.fixture
    def timeout(self, cls):
        return cls(*self.base_args, error_type='timeout',
                   error_message='timeout')

    def test_object_is_error(self, obj):
        assert obj.is_error
