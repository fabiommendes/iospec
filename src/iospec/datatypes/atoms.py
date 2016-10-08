import collections
import copy
import re

from unidecode import unidecode


class Atom(collections.UserString):
    """
    Base class for all atomic elements.
    """

    is_input = is_output = is_expanded = is_safe = is_complete = False
    escape_chars = {
        '<': '\\<',
        '$': '\\$',
        '...': '\\...',
    }

    @classmethod
    def from_json(cls, data):
        """
        Convert data created with to_json() back to a valid Atom object.
        """

        klass = {
            'In': In,
            'Out': Out,
        }[data[0]]

        return klass(data[1])

    def __init__(self, data, lineno=None):
        super().__init__(data)
        self.lineno = lineno

    def __str__(self):
        return self.data

    def __repr__(self):
        return '%s(%r)' % (type(self).__name__, self.data)

    def __eq__(self, other):
        if type(self) is type(other):
            return self.data == other.data
        elif isinstance(other, str):
            return self.data == other
        return NotImplemented

    def _escape(self, st):
        for c, esc in self.escape_chars.items():
            st = st.replace(c, esc)
        return st

    def _un_escape(self, st):
        for c, esc in self.escape_chars.items():
            st = st.replace(esc, c)
        return st

    def source(self):
        """
        Expand node as an iospec source code.
        """

        return self._escape(self.data)

    def copy(self):
        """
        Return a copy.
        """

        return copy.copy(self)

    def transform(self, func):
        """
        Return a transformed version of itself by the given function.
        """

        new = copy.copy(self)
        new.data = func(new.data)
        return new

    def normalize_presentation(self):
        """
        Normalize string to compare with other strings when looking for
        presentation errors.
        """

        return self.transform(lambda x: unidecode(x.casefold().strip()))

    def to_json(self):
        """
        Return a pair of [type, data] that can be converted to valid json.
        """

        return [type(self).__name__, str(self)]


class Comment(Atom):
    """
    A raw block of comments.
    """

    type = 'comment'
    is_complete = is_safe = is_expanded = True

    def source(self):
        return self.data

    def content(self):
        return '\n'.join(line[1:] for line in self.data.splitlines() if line)


class InOrOut(Atom):
    """
    Common interfaces to In and Out classes.
    """

    ELLIPSIS_MATCH = re.compile(r'(?:^\.\.\.|[^\\]\.\.\.)')

    def __init__(self, data, fromsource=False, lineno=None):
        if fromsource:
            data = self._un_escape(data)
        super().__init__(data, lineno=lineno)


class In(InOrOut):
    """
    Plain input string.
    """

    type = 'input'
    is_input = is_safe = is_complete = is_expanded = True

    def source(self):
        return '<%s>\n' % super().source()


class OutOrEllipsis(InOrOut):
    is_output = is_safe = is_complete = is_expanded = True

    @classmethod
    def is_ellipsis(cls, data):
        """
        Return True if input data should correspond to an OutEllipsis object.
        """

        return cls.ELLIPSIS_MATCH.search(data) is not None

    @staticmethod
    def _requires_line_escape(line):
        return (not line) or line[0] in '#|'

    @staticmethod
    def _line_escape(line):
        return '||' + line if line.startswith('|') else '|' + line

    def source(self):
        data = super().source()
        lines = data.split('\n')
        if any(self._requires_line_escape(line) for line in lines):
            data = '\n'.join(self._line_escape(line) for line in lines)
        return data


class Out(OutOrEllipsis):
    """
    Plain output string.
    """

    type = 'output'


class OutEllipsis(Out):
    """
    An output string with an ellipsis character.
    """

    type = 'ellipsis'
    escape_chars = dict(Out.escape_chars)
    escape_chars.pop('...', None)

    def __init__(self, data, **kwargs):
        super().__init__(data, **kwargs)
        self.parts = self.ELLIPSIS_MATCH.split(self.data)
        self.parts = tuple(part.replace('\\...', '...') for part in self.parts)

    def __eq__(self, other):
        if isinstance(other, (str, Out)):
            data = str(other)
            parts = list(self.parts)

            # Check the beginning of the string. If we pass the stage, the rule
            # is to match any content in the beginning of the data string.
            if parts[0] and data.startswith(parts[0]):
                data = data[len(parts[0]):]
                parts.pop(0)
            elif parts[0]:
                return False

            # Evaluate all possible matches consuming the template from the end
            # of the string
            while parts:
                end = parts.pop()
                if data.endswith(end):
                    data = data[:-len(end)]
                    if not parts:
                        return True
                    else:
                        data, sep, tail = data.rpartition(parts[-1])
                        if not sep:
                            return False
                        parts.pop()
                else:
                    return False
            return True
        return super().__eq__(other)


class OutRegex(InOrOut):
    """
    A regex matcher string.
    """

    type = 'regex'
    is_output = is_complete = is_safe = is_expanded = True

    def source(self):
        return '/%s/' % super().source()


class Command(Atom):
    """
    A computed input of the form $name(args).

    Args:
        name (str)
            Name of the compute input
        args (str)
            The string between parenthesis
        factory (callable)
            A function that is used to generate new input values.
        parsed_args
            The parsed argument string.
    """

    type = 'command'
    is_input = True

    # TODO: mark built in commands as safe.
    @property
    def is_safe(self):
        return False

    def __init__(self, name, args=None, factory=None, lineno=None):
        self.name = name
        self.args = args
        self.factory = factory or self.source
        super().__init__('', lineno=lineno)

    def __repr__(self):
        if self.args is None:
            return '%s(%r)' % (type(self).__name__, self.name)
        else:
            return '%s(%r, %r)' % (type(self).__name__, self.name, self.args)

    @property
    def data(self):
        return self.source().rstrip('\n')

    @data.setter
    def data(self, value):
        if value:
            raise AttributeError('setting data to %r' % value)

    def expand(self):
        """Expand command into a In() atom."""

        return In(str(self.factory()), lineno=self.lineno)

    def generate(self):
        """Generate a new value from the factory function."""

        return self.factory()

    def source(self):
        if self.args is None:
            return '$%s\n' % self.name
        else:
            escaped_args = self._escape(self.args)
            return '$%s(%s)\n' % (self.name, escaped_args)


class CommentDeque(collections.deque):
    """
    A deque with a .comment string attribute.
    """
    __slots__ = ['comment']

    def __init__(self, data=(), comment=None):
        self.comment = comment
        super().__init__(data)