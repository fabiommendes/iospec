import pytest
from iospec import parse_string as ioparse
from iospec import feedback


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
        'foo:<bar>\n'
        'hi bar!'
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

if __name__ == '__main__':
    pytest.main('test_feedback.py')
