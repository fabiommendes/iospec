import pytest
from iospec import parse


# Some iospec examples
from iospec.feedback import feedback

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


def test_copy_produces_identical_objects(source):
    ast = parse(source)
    assert ast.to_json() == ast.copy().to_json()


def test_normalization_is_idempotent(source):
    ast1 = parse(source)

    ast2 = ast1.copy()
    ast2.normalize()
    ast3 = ast2.copy()
    ast3.normalize()
    assert ast2 == ast3
    assert ast2.to_json() == ast3.to_json()

    # Now with stream=True normalization
    ast2 = ast1.copy()
    ast2.normalize(stream=True)
    ast3 = ast2.copy()
    ast3.normalize(stream=True)
    print('-------')
    ast2.pprint()
    ast3.pprint()
    assert ast2 == ast3
    assert ast2.to_json() == ast3.to_json()


def test_parse_runtime_error_block_with_error_message():
    src = RENDER_BACK_SOURCES['runtime error with message']
    ast = parse(src)
    case = ast[0]
    assert len(case.get_testcase()) == 3
    assert case.error_message == 'RuntimeError: some error'


def test_system_streams_normalization():
    src = RENDER_BACK_SOURCES['simple example']
    ast = parse(src)
    ast.normalize(stream=True)
    assert len(ast) == 1

    testcase = ast[0]
    assert testcase[0].is_input
    assert testcase[1].is_output
    assert len(testcase) == 2

    x, y = testcase
    assert x == 'bar'
    assert y == 'foo: foobar'


def test_system_streams_feedback_comparison():
    key = parse(RENDER_BACK_SOURCES['simple example'])
    equiv = ('<bar>\n'
             'foo: foobar')
    equiv = parse(equiv)
    key2 = key.copy()
    key2.normalize(stream=True)
    assert key2[:] == equiv[:]
    del equiv[0][0]
    equiv.pprint()
    fb1 = feedback(equiv, key, stream=False)
    fb2 = feedback(equiv, key, stream=True)
    assert fb1.status != fb2.status
    assert not fb1.is_correct
    assert fb2.is_correct

