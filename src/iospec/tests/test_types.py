import json
from numbers import Number

import pytest

import iospec
from iospec import ErrorTestCase
from iospec import StandardTestCase, In, Out


class AbstractTestCase:
    base_cls = None
    base_args = ()
    base_type = None
    base_json = {}
    base_inputs = None

    @pytest.fixture
    def cls(self):
        return self.base_cls

    @pytest.fixture
    def obj(self):
        return self.base_cls(*self.base_args)

    @pytest.fixture
    def inputs(self):
        return self.base_inputs

    def test_has_type(self, obj):
        assert obj.type == self.base_type

    def test_has_a_default_priority(self, obj):
        assert isinstance(obj.priority, Number)

    def test_can_override_priority(self, obj):
        obj.priority = 42
        assert obj.priority == 42

    def test_object_is_simple(self, obj):
        assert not obj.is_standard_test_case

    def test_object_is_expanded(self, obj):
        assert obj.is_expanded

    def test_object_is_input(self, obj):
        assert not obj.is_input

    def test_object_is_error(self, obj):
        assert not obj.is_error_test_case

    #
    # JSON representation
    #
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

    def test_object_creates_list_of_inputs(self, obj, inputs):
        input_list = obj.inputs()
        assert input_list == inputs

    def assert_valid_json(self, data):
        dump = json.dumps(data)
        reconstructed = json.loads(dump)
        assert reconstructed == data


class TestStandardTestCase(AbstractTestCase):
    base_cls = iospec.StandardTestCase
    base_args = ([Out('foo'), In('bar')],)
    base_type = 'standard'
    base_json = {'type': 'standard', 'data': [['Out', 'foo'], ['In', 'bar']]}
    base_inputs = ['bar']

    def test_object_is_simple(self, obj):
        assert obj.is_standard_test_case


class TestInputTestCase(AbstractTestCase):
    base_cls = iospec.InputTestCase
    base_args = (['foo', 'bar'],)
    base_type = 'input'
    base_json = {'type': 'input', 'data': [['In', 'foo'], ['In', 'bar']]}
    base_inputs = ['foo', 'bar']

    def test_object_is_input(self, obj):
        assert obj.is_input


class TestErrorTestCase(AbstractTestCase):
    base_cls = iospec.ErrorTestCase
    base_args = TestStandardTestCase.base_args
    base_inputs = TestStandardTestCase.base_inputs
    base_type = 'error'
    base_json = dict(TestStandardTestCase.base_json,
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
        assert obj.is_error_test_case

    def test_error_get_error_info(self, obj):
        ex1 = obj.get_exception()
        ex2 = RuntimeError('error')
        assert ex1.args == ex2.args
        assert type(ex1) is type(ex2)
        assert obj.get_error_message() == 'error'

    def test_raise_exception(self, obj):
        with pytest.raises(RuntimeError):
            obj.raise_exception()

    def test_build_error_do_accept_data_attr(self, build):
        with pytest.raises(ValueError):
            ErrorTestCase([Out('foo'), In('bar')], error_type='build')

    def test_build_error_json_has_no_data(self, build):
        assert not build.to_json()['data']

    def test_build_error_normalization_do_not_insert_spurious_data(self, build: ErrorTestCase):
        assert build.error_type == 'build'
        assert not build.to_json()['data']
        build._normalize_trailing_spaces()
        build._normalize_in_out_streams()
        build._normalize_in_out_strings()
        build._join_out_strings()
        build.fuse_outputs()
        assert not build.to_json()['data']


#
# Generic tests that are not bound to specific test case types
#
class TestExamples:
    def test_normalize_consecutive_outputs(self):
        tc = StandardTestCase([Out('foo'), Out('bar'), In('baz'), Out('eggs')])
        tc.normalize()
        assert list(tc) == [Out('foo\nbar'), In('baz'), Out('eggs')]

    def test_normalize_alternate_in_out_strings(self):
        tc = StandardTestCase([Out('bar'), In('baz'), In('zaz'), Out('eggs')])
        tc.normalize()
        assert list(tc) == [Out('bar'), In('baz'), Out(''), In('zaz'),
                            Out('eggs')]

    def test_normalize_start_with_out_string(self):
        tc = StandardTestCase([In('bar'), In('baz'), Out('eggs')])
        tc.normalize()
        assert list(tc) == [Out(''), In('bar'), Out(''), In('baz'), Out('eggs')]

    def test_remove_trailing_spaces(self):
        tc = StandardTestCase([Out('bar '), In('baz'), Out('eggs \nbaz\n')])
        tc.normalize()
        assert list(tc) == [Out('bar '), In('baz'), Out('eggs\nbaz')]

    def test_normalize_iospec(self):
        src = '<bar>\n<baz>\nfoobar\n\nfoo <bar>\nfoobar'
        ast = iospec.parse(src)
        ast2 = iospec.parse(src)
        ast.normalize()
        case1, case2 = ast
        assert list(case1) == [Out(''), In('bar'), Out(''), In('baz'),
                               Out('foobar')]
        assert case2 == ast2[1]
