import pytest
from iospec import parse


# Some iospec examples
RENDER_BACK_SOURCES = """
# simple example
foo: <bar>
foobar


### simple computed
foo: $name
foobar


### computed with argument
foo: $name(10)
foobar


### multi-input
<foo>
<bar>
foo bar


### import definition
@import math
@from math import sqrt


### command definition
@command
def foo(*args):
    return 1


### block input
@input
    foo
    $name
    $int(10)


### inline input
@input foo;$name;$int(10)


### consecutive inline inputs
@input $name
@input bar
@plain foo
@plain bar


### consecutive block inputs
@input
    $name

@input
    bar

@plain
    foo

@plain
    bar


### block plain input
@plain
    foo
    $foobar
    $baz


### inline plain
@plain foo;$foobar;tl\;dr


### build error
@build-error
    SyntaxError: invalid syntax


### timeout error
@timeout-error
    foo: <bar>
    bar


### runtime error
@runtime-error
    foo: <bar>
    bar


### runtime error with message
@runtime-error
    foo: <bar>
    bar

@error
    RuntimeError: some error
""".strip()
RENDER_BACK_SOURCES = {
    par.partition('\n')[0][2:]: par
    for par in RENDER_BACK_SOURCES.split('##')
    if par
}


@pytest.fixture(params=RENDER_BACK_SOURCES)
def source(request):
    data = RENDER_BACK_SOURCES[request.param]
    data = data.splitlines()
    if data[0].startswith('#'):
        del data[0]
    return '\n'.join(data)


def test_render_simple_test_case_block_correctly(source):
    parsed = parse(source)
    assert source.rstrip() == parsed.source().rstrip()


def test_render_normalized_test_case_block_correctly(source):
    parsed = parse(source)
    parsed.normalize()
    assert source.rstrip() == parsed.source().rstrip()


def test_parse_runtime_error_block_with_error_message():
    src = RENDER_BACK_SOURCES['runtime error with message']
    ast = parse(src)
    case = ast[0]
    assert len(case.get_test_case()) == 3
    assert case.error_message == 'RuntimeError: some error'

