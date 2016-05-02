import decimal
import jinja2
from iospec.util import tex_escape
from iospec.types import TestCase, IoSpec
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
    """User feedback.

    Parameters
    ----------

    value : TestCase
        pass
    title: str
        Title of the message (e.g., Wrong answer)
    """
    
    def __init__(self, case, answer_key,
                 grade=decimal.Decimal(1), status='ok', message=None,
                 hint=None):

        self.case = case
        self.answer_key = answer_key
        self.grade = grade
        self.status = status
        self.hint = hint
        self.message = message

    @property
    def is_correct(self):
        return self.status == 'ok'

    @property
    def title(self):
        return error_titles[self.status]

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
            'case': self.case,
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
        data = dict(self.__dict__)
        data['case'] = self.case.to_json()
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
def get_feedback(response: TestCase, answer_key: TestCase):
    """Return a feedback structure that represents the success/error for a
    single testcase."""

    if list(response) == list(answer_key):
        return Feedback(response, answer_key)

    feedback = Feedback(response, answer_key, grade=decimal.Decimal(0))

    # Presentation errors
    if presentation_equal(response, answer_key):
        feedback.status = 'wrong-presentation'
        feedback.grade = decimal.Decimal(0.5)

    # Wrong answer
    elif response.type.startswith('io'):
        feedback.status = 'wrong-answer'

    # Error messages
    elif response.type.startswith('error'):
        feedback.status = response.type
    else:
        raise ValueError('invalid testcase: \n%s' % response.format())

    return feedback


@get_feedback.overload
def _(response: IoSpec, answer_key: IoSpec):
    value = decimal.Decimal(1)
    feedback = None

    for resp, key in zip(response, answer_key):
        curr_feedback = get_feedback(resp, key)

        if feedback is None:
            feedback = curr_feedback

        if curr_feedback.grade < value:
            feedback = curr_feedback
            value = curr_feedback.grade

            if value == 0:
                break

    return feedback


def presentation_equal(case1, case2):
    """Return True if both cases are equal after casefolding and stripping all
    spaces"""

    #TODO: implement
    return case1 == case2
