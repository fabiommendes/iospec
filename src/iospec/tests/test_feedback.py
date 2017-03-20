import pytest

from iospec import feedback
from iospec import parse as ioparse
from iospec.feedback import Feedback


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
    return feedback.get_feedback(tree_ok[0], tree_ok[0])


@pytest.fixture
def feedback_wrong(tree_ok, tree_wrong):
    return feedback.get_feedback(tree_wrong[0], tree_ok[0])


@pytest.fixture
def feedback_presentation(tree_ok, tree_presentation):
    return feedback.get_feedback(tree_presentation[0], tree_ok[0])


def test_ok_feedback(feedback_ok):
    fb = feedback_ok
    txt = fb.render_text()
    html = fb.render_html()
    tex = fb.render_latex()
    message = 'Congratulations!'
    assert repr(feedback_ok) == '<Feedback: ok (1.00)>'
    assert fb.grade == 1
    assert message in txt
    assert message in html
    assert message in tex


def test_wrong_feedback(feedback_wrong):
    fb = feedback_wrong
    txt = fb.render_text()
    html = fb.render_html()
    tex = fb.render_latex()
    message = 'Wrong Answer'
    assert fb.grade == 0
    assert message in txt
    assert message in html
    assert message in tex
    assert fb.get_error_message() == ''


def test_presentation(feedback_presentation):
    fb = feedback_presentation
    txt = fb.render_text()
    html = fb.render_html()
    tex = fb.render_latex()
    message = 'Presentation Error'
    assert fb.grade == 0.5
    assert message in txt
    assert message in html
    assert message in tex


def test_hello_wrong():
    correct = ioparse('hello world!')
    wrong = ioparse('hi world!')
    fb = feedback.get_feedback(wrong[0], correct[0])
    txt = fb.render_text()
    html = fb.render_html()
    tex = fb.render_latex()
    message = 'Wrong Answer'
    assert fb.grade == 0
    assert message in txt
    assert message in html
    assert message in tex


def test_equality(feedback_ok, feedback_wrong):
    assert feedback_ok != feedback_wrong
    json = feedback_ok.to_json()
    f1 = Feedback.from_json(json)
    f2 = Feedback.from_json(json)
    assert f1 == f2


def test_feedback_from_json(feedback_ok):
    json = {'answer_key': {
        'data': [['Out', 'foo: '], ['In', 'bar'], ['Out', 'hi bar!']],
        'type': 'standard'},
        'grade': 1.0,
        'hint': None,
        'message': None,
        'status': 'ok',
        'testcase': {
            'data': [['Out', 'foo: '], ['In', 'bar'], ['Out', 'hi bar!']],
            'type': 'standard'}}
    assert json == feedback_ok.to_json()
    data = Feedback.from_json(json)
    assert data == feedback_ok


def test_feedback_receive_grade(feedback_ok):
    feedback_ok.grade = 0
    feedback_ok.compute_grade()
    assert feedback_ok.grade == 1


def test_render_methods_for_bad_case(feedback_wrong):
    fb = feedback_wrong
    assert 'foo' in fb.render_text()
    assert 'foo' in fb.render_color()
    assert 'foo' in fb.render_html()
    assert 'foo' in fb.render_latex()


def test_render_methods_for_good_case(feedback_ok):
    fb = feedback_ok
    assert 'Congratulations' in fb.render_text()
    assert 'Congratulations' in fb.render_color()
    assert 'Congratulations' in fb.render_html()
    assert 'Congratulations' in fb.render_latex()


def test_feedback_function_accepts_iospec(tree_ok, tree_wrong, feedback_wrong):
    fb = feedback.get_feedback(tree_wrong, tree_ok)
    assert fb == feedback_wrong
