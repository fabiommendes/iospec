import json
import os

import pytest

import iospec
from iospec import parse


#
# Example fixtures
#
@pytest.fixture(
    params=['inputs']
)
def example_src(request):
    name = request.param
    dir = os.path.dirname(__file__)
    dir = os.path.join(dir, 'examples')

    with open(os.path.join(dir, name + '.io')) as F:
        iospec_src = F.read()

    with open(os.path.join(dir, name + '.json')) as F:
        json_src = F.read()

    return iospec_src, json_src


@pytest.fixture
def example_pair(example_src):
    src, json_src = example_src
    ast = iospec.parse(src)
    json_data = json.loads(json_src)
    return ast, json_data


@pytest.fixture
def example_json(example_pair):
    return example_pair[1]


@pytest.fixture
def example_iospec(example_pair):
    return example_pair[0]


@pytest.fixture
def example_iospec_json(example_iospec):
    return example_iospec.to_json()


#
# Sample IoSpec source data
#
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


@pytest.fixture
def spec_with_error():
    return parse('''foo <bar>
barfoo

@runtime-error
    foo <42>
@error
    invalid name: 42
''')


def test_project_defines_author_and_version():
    assert hasattr(iospec, '__author__')
    assert hasattr(iospec, '__version__')


def test_examples(example_iospec, example_json):
    assert example_iospec.to_json() == example_json


def test_can_get_error_data(spec_with_error):
    io = spec_with_error
    assert io.has_errors
    assert io.get_error_type() == 'runtime'
    assert io.get_error_message() == 'invalid name: 42'
    ex = io.get_exception()
    assert isinstance(ex, RuntimeError)
    assert ex.args == ('invalid name: 42',)


def test_error_data_on_good_source(spec1):
    io = spec1
    assert not io.has_errors
    assert io.get_error_type() is None
    assert io.get_error_message() is None
    assert io.get_exception() is None
