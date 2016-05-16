import pytest
from iospec import parse_string as ioparse
from iospec import feedback


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


if __name__ == '__main__':
    pytest.main('test_feedback_bugs.py')
