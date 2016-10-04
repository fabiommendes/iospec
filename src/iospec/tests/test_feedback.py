import pytest

from iospec import feedback
from iospec import parse as ioparse


@pytest.fixture
def tree_ok():
    return ioparse(
        'foo: <bar>\n'
        'hi bar!'
    )


@pytest.fixture
def tree_wrong():
    return ioparse(
        'foo: <bar>\n'
        'bar'
    )


@pytest.fixture
def tree_presentation():
    return ioparse(
        'Foo:<bar>\n'
        'Hi Bar!'
    )


@pytest.fixture
def feedback_ok(tree_ok):
    return feedback.feedback(tree_ok[0], tree_ok[0])


@pytest.fixture
def feedback_wrong(tree_ok, tree_wrong):
    return feedback.feedback(tree_wrong[0], tree_ok[0])


@pytest.fixture
def feedback_presentation(tree_ok, tree_presentation):
    return feedback.feedback(tree_presentation[0], tree_ok[0])


def test_ok_feedback(feedback_ok):
    fb = feedback_ok
    txt = fb.as_text()
    html = fb.as_html()
    tex = fb.as_latex()
    message = 'Congratulations!'
    assert fb.grade == 1
    assert message in txt
    assert message in html
    assert message in tex


def test_wrong_feedback(feedback_wrong):
    fb = feedback_wrong
    txt = fb.as_text()
    html = fb.as_html()
    tex = fb.as_latex()
    message = 'Wrong Answer'
    assert fb.grade == 0
    assert message in txt
    assert message in html
    assert message in tex


def test_presentation(feedback_presentation):
    fb = feedback_presentation
    txt = fb.as_text()
    html = fb.as_html()
    tex = fb.as_latex()
    message = 'Presentation Error'
    assert fb.grade == 0.5
    assert message in txt
    assert message in html
    assert message in tex


def test_hello_wrong():
    correct = ioparse('hello world!')
    wrong = ioparse('hi world!')
    fb = feedback.feedback(wrong[0], correct[0])
    txt = fb.as_text()
    html = fb.as_html()
    tex = fb.as_latex()
    message = 'Wrong Answer'
    assert fb.grade == 0
    assert message in txt
    assert message in html
    assert message in tex
