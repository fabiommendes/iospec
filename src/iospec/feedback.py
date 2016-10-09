import decimal
import pprint

import jinja2
from generic import generic

from iospec.datatypes import TestCase, SimpleTestCase, ErrorTestCase, IoSpec
from iospec.utils import tex_escape

# Module constants
error_titles = {
    'ok': 'Correct Answer',
    'wrong-answer': 'Wrong Answer',
    'presentation-error': 'Presentation Error',
    'timeout-error': 'Timeout Error',
    'runtime-error': 'Runtime Error',
    'build-error': 'Build Error',
}

jinja_loader = jinja2.PackageLoader('iospec')
jinja_env = jinja2.Environment(
    loader=jinja_loader,
    trim_blocks=True,
    lstrip_blocks=True
)
latex_env = jinja2.Environment(
    loader=jinja_loader,
    trim_blocks=True,
    lstrip_blocks=True,
    block_start_string='((*',
    block_end_string='*))',
    variable_start_string='\\var{',
    variable_end_string='}'
)
latex_env.filters['escape'] = tex_escape


class Feedback:
    """
    Represents the user feedback after comparing the results of running a
    program in a test case with the expected results in the answer key.

    Args:
        testcase: :cls:`iospec.TestCase`
            The test case representing a single run of a program.
        answer_key: :cls:`iospec.TestCase`
            The expected test case object which represents a correct answer.
        grade: Decimal
            The grade given after comparing both TestCase instances.
        status:
            The status string for the feedback message. Represents which kind
            of error/success occurred. Can be any of these strings:

            ok:
                The testcase answer is correct.
            error-presentation:
                Program finished execution and probably computed the correct
                answer. However it was presented incorrectly. The default
                strategy is a bit simplistic: we compare a case-folded and
                whitespace-stripped version of each solution to see if they
                are the same after transformation.
            wrong-answer:
                Program finished execution, but produced a wrong answer.
            error-timeout:
                Program was interrupted before completion because it reached the
                timeout limit.
            error-runtime:
                Execution finished with an exception or any non-zero return
                value.
            error-build:
                Program could not be built. Typically this error is due to
                syntax errors or because the program uses unsupported libraries.
        message:
            An additional message that helps to explain the status code. This is
            optional and can be ignored in a few status codes.
        hint:
            An optional hint that can be given to the student to help overcome
            some error or improve its solution.
        """

    VALID_STATUS = {'ok', 'wrong-answer', 'presentation-error', 'timeout-error',
                    'build-error', 'runtime-error'}
    STATUS_MAP = {
        'wrong-presentation': 'presentation-error',
        'error-timeout': 'timeout-error',
        'error-build': 'build-error',
        'error-runtime': 'runtime-error',
    }
    is_correct = property(lambda x: x.status == 'ok')
    is_wrong_answer= property(lambda x: x.status == 'wrong-answer')
    is_presentation_error = property(lambda x: x.status == 'presentation-error')
    is_timeout_error = property(lambda x: x.status == 'timeout-error')
    is_build_error = property(lambda x: x.status == 'build-error')
    is_runtime_error = property(lambda x: x.status == 'runtime-error')

    @property
    def title(self):
        """
        Convert status into a human readable text.
        """

        return error_titles[self.status]

    @classmethod
    def grading(cls, testcase, answer_key):
        """
        Create Feedback object from testcase and answer_key preforming an
        automatic grading.
        """

        return feedback(testcase, answer_key)

    @classmethod
    def from_json(cls, data):
        if 'testcase' not in data or 'answer_key' not in data:
            raise ValueError('missing testcase or answer key fields in JSON '
                             'data %r' % data)
        kwargs = dict(data)
        testcase = TestCase.from_json(kwargs.pop('testcase'))
        answer_key = TestCase.from_json(kwargs.pop('answer_key'))

        # Update from old form of status strings
        status = data['status']
        kwargs['status'] = cls.STATUS_MAP.get(status, status)
        return Feedback(testcase, answer_key, **kwargs)

    def __init__(self, testcase, answer_key, grade, status, message=None,
                 hint=None):
        if status not in self.VALID_STATUS:
            raise ValueError('invalid status: %r' % status)
        self.testcase = testcase
        self.answer_key = answer_key
        self.grade = decimal.Decimal(grade)
        self.status = status
        self.hint = hint
        self.message = message

    def __repr__(self):
        return '<Feedback: %s (%.2f)>' % (self.status, self.grade)

    def compute_grade(self):
        """
        Compute the grade and feedback status from the testcase and answer key.
        """

        out = feedback(self.testcase, self.answer_key)
        self.grade = out.grade
        self.answer_key = out.answer_key
        if self.message is None:
            self.message = out.message
        if self.hint is None:
            self.hint = out.hint

    def get_error_message(self):
        """
        Return error message when it exists.
        """

        return self.testcase.get_error_message()

    def render(self, method='text', **kwds):
        """
        Render object using the specified method.
        """

        try:
            render_format = getattr(self, 'as_' + method)
        except AttributeError:
            raise ValueError('unknown format: %r' % method)
        else:
            return render_format(**kwds)

    def as_text(self):
        """Plain text rendering"""

        return self._render('feedback.txt', color=disabled)

    def as_color(self):
        """Plain text rendering with terminal colors."""

        return self._render('feedback.txt', color=color)

    def as_html(self):
        """Render to an html div. Same as as_div()"""

        return self._render('feedback-div.html')

    def as_div(self):
        """Render to an html div."""

        return self._render('feedback-div.html')

    def as_latex(self):
        """Render to latex."""

        return self._render('feedback.tex', latex=True)

    def _render(self, template, latex=False, **kwds):
        context = {
            'case': self.testcase,
            'answer_key': self.answer_key,
            'grade': self.grade,
            'status': self.status,
            'title': self.title,
            'hint': self.hint,
            'message': self.message,
            'is_correct': self.is_correct,
            'h1': self._over_underline,
            'h2': self._underline,
        }

        # Get template
        if latex:
            template = latex_env.get_template(template)
        else:
            template = jinja_env.get_template(template)

        # Render it!
        context.update(kwds)
        data = template.render(**context)
        if data.endswith('\n'):
            return data[:-1]
        return data

    @staticmethod
    def _over_underline(st, symbol='='):
        st = (st or '   ').replace('\t', '    ')
        size = max(len(line) for line in st.splitlines())
        line = symbol * size
        return '%s\n%s\n%s' % (line, st, line)

    @staticmethod
    def _underline(st, symbol='='):
        st = (st or '   ').replace('\t', '    ')
        size = max(len(line) for line in st.splitlines())
        line = symbol * size
        return '%s\n%s' % (st, line)

    @staticmethod
    def _overline(st, symbol='='):
        st = (st or '   ').replace('\t', '    ')
        size = max(len(line) for line in st.splitlines())
        line = symbol * size
        return '%s\n%s' % (line, st)

    def to_json(self):
        """
        Convert feedback to a JSON compatible structure of dictionaries and
        lists.
        """

        if not hasattr(self, 'testcase'):
            self.testcase = self.case
            del self.case

        data = dict(self.__dict__)
        data['testcase'] = self.testcase.to_json()
        data['answer_key'] = self.answer_key.to_json()
        data['grade'] = float(self.grade)
        return data

    def pprint(self):
        """
        Pretty prints feedback.

        Useful for debugging.
        """

        print(self.pformat())

    def pformat(self):
        """
        Similar to .pprint(), but returns a string instead.
        """

        return pprint.pformat(self.to_json())


#
# Color support
# See: https://en.wikipedia.org/wiki/ANSI_escape_code
#
class color:
    HEADER = '\033[1m\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    INPUTVALUE = BOLD + FAIL


class disabled:
    HEADER = ''
    OKBLUE = ''
    OKGREEN = ''
    WARNING = ''
    FAIL = ''
    ENDC = ''
    BOLD = ''
    UNDERLINE = ''
    INPUTVALUE = ''


@generic
def feedback(response: TestCase, answer_key: TestCase, stream=False):
    """
    Return a feedback structure that represents the success/error for a single
    test case.

    Args:
        response, answer_key (TestCase):
            The response and answer key test case structures.
        stream (bool):
            If True, compares both components by the C-stream interaction. Each
            argument is normalized with x.normalize(stream=True) and the
            normalized version is saved on the resulting feedback structure.
    """

    response = response.copy()
    answer_key = answer_key.copy()
    response.normalize(stream=stream)
    answer_key.normalize(stream=stream)
    grade = decimal.Decimal(0)

    # Error messages
    if isinstance(response, ErrorTestCase):
        status = response.error_type + '-error'

    # Correct response
    elif list(response) == list(answer_key):
        status = 'ok'
        grade = decimal.Decimal(1.0)

    # Presentation errors
    elif presentation_equal(response, answer_key):
        status = 'presentation-error'
        grade = decimal.Decimal(0.5)

    # Wrong answer
    elif isinstance(response, SimpleTestCase):
        status = 'wrong-answer'

    # Invalid
    else:
        raise ValueError('invalid testcase: \n%s' % response.format())

    return Feedback(response, answer_key, grade=grade, status=status)


@feedback.overload
def _(response: IoSpec, answer_key: IoSpec, **kwargs):
    fb = None
    value = decimal.Decimal(1)

    for case, answer_key in zip(response, answer_key):
        curr_feedback = feedback(case, answer_key, **kwargs)
        if fb is None:
            fb = curr_feedback
        if curr_feedback.grade < value:
            fb = curr_feedback
            value = curr_feedback.grade
            if value == 0:
                break
    return fb


def presentation_equal(case1, case2):
    """
    Return True if both cases are equal after case-folding and stripping all
    whitespace.
    """

    return case1.isequal(case2, casefold=True, skip_spaces=True)
