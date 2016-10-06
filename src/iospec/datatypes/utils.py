from collections import deque

from generic import generic

from iospec.utils import indent


class AttrDict(dict):
    """
    Dictionary that accept attribute access.
    """

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError

    def __setattr__(self, key, value):
        self[key] = value


class TestCaseDiff:
    """
    Represents the difference of two test cases.
    """

    @property
    def is_different(self):
        self.digest()
        return self.diff_type is not None

    def __init__(self, answer_key, response):
        self.left = normalize_testcase(answer_key)
        self.right = normalize_testcase(response)
        self._left_q = deque(self.left)
        self._right_q = deque(self.right)
        self._common = deque()
        self._digest = False
        self.diff_type = None
        self.diff_left_line = ''
        self.diff_right_line = ''
        self.common_source = None
        self.common = None

    def __str__(self):
        return self.render()

    def render(self):
        """
        Renders diff object as text.
        """

        self.digest()
        data = [indent(self.common_source, 4)]
        if self.diff_type is None:
            return '\n'.join(data)

        data.append('----')
        data.append('-   ' + self.diff_left_line)
        data.append('+   ' + self.diff_right_line)
        data.append(self.diff_type)
        return '\n'.join(data)

    def digest(self):
        if self._digest is False:
            from iospec.datatypes import SimpleTestCase
            self._extract_common()
            self.diff_type = self._compute_error()
            self.common = SimpleTestCase(self._common)
            self.common_source = self.common.source()
            self._digest = True

    def _extract_common(self):
        left, right = self._left_q, self._right_q
        while left and right:
            x, y = left.popleft(), right.popleft()
            if x == y:
                self._common.append(y)
                continue

            if type(x) is not type(y):
                break

            x, y = self._consume_common(x, y)
            break
        else:
            return

        # Handle different values
        left.appendleft(x)
        right.appendleft(y)

    def _consume_common(self, x, y):
        return x, y

    def _compute_error(self):
        left, right = self._left_q, self._right_q
        if not left and not right:
            return

        self.diff_left_line = left.popleft().source().rstrip()
        self.diff_right_line = right.popleft().source().rstrip()
        return 'different-lines'


@generic
def isequal(x, y, **kwargs):
    """
    Return True if two objects are equal up to some normalization.
    """

    return x == y


def testcase_diff(x, y):
    """
    Return the difference between two test cases.
    """

    differ = TestCaseDiff(x, y)
    differ.digest()
    return differ


def normalize_testcase(x):
    from iospec.datatypes import SimpleTestCase

    if not isinstance(x, SimpleTestCase):
        tname = x.__class__.__name__
        raise TypeError('expected a SimpleTestCase, not %s' % tname)

    if not x.is_expanded:
        raise ValueError('Only supports expanded test cases')

    x = x.copy()
    x.normalize()
    return x