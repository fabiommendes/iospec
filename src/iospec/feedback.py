import decimal
import jinja2
from iospec.util import tex_escape
from iospec.types import TestCase, IoTestCase, ErrorTestCase, IoSpec
from generic import generic

# Module constants
error_titles = {
    'ok': 'Correct Answer',
    'wrong-answer': 'Wrong Answer',
    'wrong-presentation': 'Presentation Error',
    'error-timeout': 'Timeout Error',
    'error-runtime': 'Runtime Error',
    'error-build': 'Build Error',
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
    """Represents the user feedback after comparing the results of running a
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
            wrong-presentation:
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
    
    def __init__(self, testcase, answer_key, *, grade, status, message=None,
                 hint=None):
        self.testcase = testcase
        self.answer_key = answer_key
        self.grade = grade
        self.status = status
        self.hint = hint
        self.message = message

    @classmethod
    def grading(cls, testcase, answer_key):
        """Create Feedback object from testcase and answer_key preforming an
        automatic grading."""

        return feedback(testcase, answer_key)

    @property
    def is_correct(self):
        """True if status is 'ok'."""
        return self.status == 'ok'

    @property
    def title(self):
        """Convert status into a human readable text."""

        return error_titles[self.status]

    def compute_grade(self):
        """Compute the grade and feedback status from the testcase and answer
        key."""

        out = feedback(self.testcase, self.answer_key)
        self.grade = out.grade
        self.answer_key = out.answer_key
        if self.message is None:
            self.message = out.message
        if self.hint is None:
            self.hint = out.hint

    def render(self, method='text', **kwds):
        """Render object using the specified method."""

        try:
            render_format = getattr(self, 'as_' + format)
        except AttributeError:
            raise ValueError('unknown format: %r' % format)
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
        ns = {
            'case': self.testcase,
            'answer_key': self.answer_key,
            'grade': self.grade,
            'status': self.status,
            'title': self.title,
            'hint': self.hint,
            'message': self.message,
            'is_correct': self.is_correct,
            'h1': self._overunderline,
            'h2': self._underline,
        }

        # Get template
        if latex:
            template = latex_env.get_template(template)
        else:
            template = jinja_env.get_template(template)

        # Render it!
        ns.update(kwds)
        data = template.render(**ns)
        if data.endswith('\n'):
            return data[:-1]
        return data

    @staticmethod
    def _overunderline(st, symbol='='):
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
        """Convert feedback to a JSON compatible structure of dictionaries and
        lists."""

        data = dict(self.__dict__)
        data['case'] = self.testcase.to_json()
        data['answer_key'] = self.answer_key.to_json()
        data['grade'] = float(self.grade)
        return data

    @classmethod
    def from_json(cls, data):
        new = object.__new__(cls)
        for k, v in data.items():
            setattr(new, k, v)
        new.case = TestCase.from_json(new.case)
        new.answer_key = TestCase.from_json(new.answer_key)
        new.grade = decimal.Decimal(new.grade)
        return new


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
    BOLD = ''
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
def feedback(response: TestCase, answer_key: TestCase):
    """Return a feedback structure that represents the success/error for a
    single testcase."""

    grade = decimal.Decimal(0)
    status = None

    # Error messages
    if isinstance(response, ErrorTestCase):
        status = response.type

    # Correct response
    elif list(response) == list(answer_key):
        status = 'ok'
        grade = decimal.Decimal(1.0)

    # Presentation errors
    elif presentation_equal(response, answer_key):
        status = 'wrong-presentation'
        grade = decimal.Decimal(0.5)

    # Wrong answer
    elif isinstance(response, IoTestCase):
        status = 'wrong-answer'

    # Invalid
    else:
        raise ValueError('invalid testcase: \n%s' % response.format())

    return Feedback(response, answer_key, grade=grade, status=status)


@feedback.overload
def _(response: IoSpec, answer_key: IoSpec):
    value = decimal.Decimal(1)
    feedback = None

    for resp, key in zip(response, answer_key):
        curr_feedback = feedback(resp, key)

        if feedback is None:
            feedback = curr_feedback

        if curr_feedback.grade < value:
            feedback = curr_feedback
            value = curr_feedback.grade

            if value == 0:
                break

    return feedback


def presentation_equal(case1, case2):
    """Return True if both cases are equal after case-folding and stripping all
    whitespace"""

    #TODO: implement
    return case1 == case2
