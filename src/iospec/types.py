import collections
import pprint
import copy
from generic import generic


__all__ = [
    # Atomic
    'Atom', 'Comment', 'In', 'Out', 'Command',

    # Nodes
    'IoSpec', 'TestCase', 'ErrorTestCase', 'IoTestCase', 'InputTestCase',

    # Functions
    'isequal', 'normalize'
]


#
# Atomic AST nodes
#
class Atom(collections.UserString):

    """Base class for all atomic elements"""

    type = 'atom'

    escape_chars = {
        '<': '\\<',
        '$': '\\$',
    }

    def __init__(self, data, *, lineno=None):
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
        """Expand node as an iospec source code."""

        return self._escape(self.data)

    def copy(self):
        """Return a copy"""

        return copy.copy(self)

    def transform(self, func):
        """Return a transformed version of itself by the given function"""

        new = copy.copy(self)
        new.data = func(new.data)
        return new

    def to_json(self):
        """Return a pair of [type_name, data] that can be converted to valid
        json."""

        return type(self).__name__, str(self)

    @classmethod
    def from_json(cls, data):
        """Convert data created with to_json() back to a valid Atom object."""

        klass = {
            'In': In,
            'Out': Out,
        }[data[0]]

        return klass(data[1])


class Comment(Atom):
    """Represent a raw block of comments"""

    def source(self):
        return self.data

    def content(self):
        return '\n'.join(line[1:] for line in self.data.splitlines() if line)


class InOrOut(Atom):
    """Common interfaces to In and Out classes"""

    def __init__(self, data, *, fromsource=False, lineno=None):
        if fromsource:
            data = self._un_escape(data)
        super().__init__(data, lineno=lineno)


class In(InOrOut):
    """Plain input string"""

    type = 'input'

    def source(self):
        return '<%s>\n' % super().source()


class Out(InOrOut):
    """Plain output string"""

    type = 'output'

    def source(self):
        data = super().source()
        lines = data.split('\n')
        if any(self._requires_line_escape(line) for line in lines):
            data = '\n'.join(self._line_escape(line) for line in lines)
        return data

    @staticmethod
    def _requires_line_escape(line):
        return (not line) or line[0] in '#|'

    @staticmethod
    def _line_escape(line):
        return '||' + line if line.startswith('|') else '|' + line


class Command(Atom):
    """A computed input of the form $name(args).

    Parameters
    ----------

    name : str
        Name of the compute input
    args : str
        The string between parenthesis
    factory : callable
        A function that is used to generate new input values.
    parsed_args : anything
        The parsed argument string.
    """

    type = 'input-command'

    def __init__(self, name,
                 args=None, factory=None, parsed_args=None, lineno=None):
        self.name = name
        self.args = args
        self.factory = factory or self.source
        self.parsed_args = parsed_args
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


#
# Container nodes for the iospec AST
#
class LinearNode(collections.MutableSequence):
    """We call a single interaction/run of a program with a set of user inputs
    a "test case".

    There are different types of case nodes, either "error-*", for representing
    failed executions, "input-*" for representing input-only specifications and
    finally "io-*", that represents both inputs and outputs of a successful
    program run.
    """
    type = 'testcase'

    def __init__(self, data=(), *, comment=None):
        self._data = []
        self.comment = (comment or '').strip()
        self.meta = {}
        if data:
            self.extend(data)

    def __iter__(self):
        for x in self._data:
            yield x

    def __getitem__(self, idx):
        if isinstance(idx, int):
            return self._data[idx]
        elif isinstance(idx, tuple):
            data = self
            for i in idx:
                data = data[i]
            return data
        else:
            raise IndexError(idx)

    def __len__(self):
        return len(self._data)

    def __setitem__(self, i, value):
        self._data[i] = value

    def __delitem__(self, i):
        del self._data[i]

    def __repr__(self):
        return super().__repr__()

    def __eq__(self, other):
        if type(self) is type(other):
            return self.__dict__ == other.__dict__
        return NotImplemented

    def source(self):
        """Render AST node as iospec source code."""

        data = ''.join(x.source() for x in self)
        return self._with_comment(data)

    def _with_comment(self, data):
        if self.comment:
            return '%s\n%s' % (self.comment, data)
        return data

    def insert(self, idx, value):
        self._data.insert(idx, None)
        try:
            self[idx] = value
        except:
            del self._data[idx]
            raise

    def pformat(self, *args, **kwds):
        """Format AST in a pprint-like format."""

        return pprint.pformat(self.json(), *args, **kwds)

    def pprint(self, *args, **kwds):
        """Pretty print AST."""

        print(self.pformat(*args, **kwds))

    def json(self):
        """JSON-like expansion of the AST.

        All linear node instances are expanded into dictionaries."""

        D = {'type': getattr(self, 'type', type(self).__name__)}
        D.update(vars(self))

        # Hide default values
        for key in ['lineno', 'comment', 'meta']:
            if key in D and not D[key]:
                del D[key]

        # Rename private attributes
        D['data'] = D.pop('_data')
        for k in ['priority', 'error']:
            if '_' + k in D:
                D[k] = value = D.pop('_' + k)
                if not value:
                    del D[k]

        memo = dict()

        def json(x):
            obj_id = id(x)

            if obj_id in memo and memo[obj_id] > 5:
                if isinstance(x, list):
                    return Literal('[...]')
                elif isinstance(x, (set, dict)):
                    return Literal('{...}')

            if hasattr(type(x), '__contains__'):
                memo[obj_id] = memo.get(obj_id, 0) + 1

            if isinstance(x, (list, tuple)):
                return [json(y) for y in x]
            elif isinstance(x, LinearNode):
                return x.json()
            elif isinstance(x, dict):
                return {k: json(v) for (k, v) in x.items()}
            else:
                return x

        return {k: json(v) for (k, v) in D.items()}

    def copy(self):
        """Return a deep copy."""

        return copy.deepcopy(self)

    def setmeta(self, attr, value):
        """Writes an attribute of meta information."""

        self.meta[attr] = value

    def getmeta(self, attr, *args):
        """Retrieves an attribute of meta information.

        Can give a second positional argument with the default value to return
        if the attribute does not exist."""

        if args:
            return self.meta.get(attr, args[0])

        try:
            return self.meta[attr]
        except KeyError:
            raise AttributeError('invalid meta attribute: %r' % attr)

    def transform_strings(self, func):
        """Transform all visible string values in test case by the given
        function *inplace*."""

        for case in self:
            case.transform_strings(func)


class IoSpec(LinearNode):
    """Root node of an iospec AST"""

    type = 'iospec-root'

    def __init__(self, data=(), *,
                 commands=None, make_commands=None, definitions=()):
        super().__init__(data)
        self.commands = AttrDict(commands or {})
        self.make_commands = AttrDict(make_commands or {})
        self.definitions = list(definitions)

    def source(self):
        prefix = '\n\n'.join(block.strip('\n') for block in self.definitions)
        return prefix + '\n\n'.join(case.source() for case in self)

    def inputs(self):
        """Return a list of input strings."""

        return [x.inputs() for x in self]

    def expand_inputs(self, size=0):
        """Expand all input command nodes into regular In() atoms.

        The changes are done *inplace*.


        Parameters
        ----------

        size:
            The target size for the total number of test cases. If the tree has
            less test cases than size, it will create additional test cases
            according to the test case priority.
        """

        if size < len(self):
            for case in self:
                case.expand_inputs()
        else:
            # Expand to reach len(self) == size
            diff = size - len(self)
            pairs = [[case.priority, case] for case in self]
            total_priority = max(sum(x[0] for x in pairs), 1)
            for x in pairs:
                x[0] *= diff / total_priority

            cases = []
            for priority, case in pairs:
                cases.append(case)
                for _ in range(round(priority)):
                    cases.append(case.copy())
            self[:] = cases

            # Expand inputs at this new size
            self.expand_inputs()

    def fuse_outputs(self):
        """Fuse any consecutive Out() strings together."""

        for case in self:
            case.fuse_outputs()

    def has_errors(self):
        """Return True if the IoSpec data has some error block"""

        return any(case.error is not None for case in self)

    def get_error(self):
        """Return an exception that describes the first error encountered in
        the run."""

        for case in self:
            if case.error is not None:
                return case.error

    def to_json(self):
        """Convert object to a json structure."""

        return [x.to_json() for x in self]

    @classmethod
    def from_json(cls, data):
        """Decode JSON representation of IoSpec data."""

        return cls([TestCase.from_json(x) for x in data])


class TestCase(LinearNode):
    """Base class for all test cases."""

    # noinspection PyArgumentList
    def __init__(self, data=(), *, priority=None, lineno=None, error=None, **kwds):
        super().__init__(data, **kwds)
        self._priority = priority
        self.lineno = lineno
        self.error = error

    @property
    def priority(self):
        if self._priority is None:
            if any(isinstance(atom, Command) for atom in self):
                return 1.0
            return 0.0
        else:
            return self._priority

    @priority.setter
    def priority(self, value):
        self._priority = value

    @property
    def is_error(self):
        return False

    @property
    def error(self):
        return self._error

    @error.setter
    def error(self, value):
        if isinstance(value, Exception):
            self._error  = value
        elif isinstance(value, type) and issubclass(value, Exception):
            self._error = value()
        elif value is None:
            self._error = value
        else:
            raise TypeError('expect exception, got %s' % value)

    def inputs(self):
        """Return a list of inputs for the test case."""

        raise NotImplementedError

    def expand_inputs(self):
        """Expand all computed input nodes *inplace*."""

        for idx, atom in enumerate(self):
            if isinstance(atom, Command):
                self[idx] = atom.expand()

    def fuse_outputs(self):
        pass

    def to_json(self):
        return {'type': self.type, 'data': [x.to_json() for x in self]}

    @classmethod
    def from_json(cls, data):
        atoms = [Atom.from_json(x) for x in data['data']]
        if data['type'] == 'io':
            return IoTestCase(atoms)
        else:
            raise NotImplementedError


class IoTestCase(TestCase):
    """Regular input/output test case."""

    @property
    def type(self):
        return 'io'

    def inputs(self):
        return [str(x) for x in self if isinstance(x, In)]

    def fuse_outputs(self):
        """Fuse consecutive Out strings together"""

        idx = 1
        while idx < len(self):
            cur = self[idx]
            prev = self[idx - 1]
            if isinstance(cur, Out) and isinstance(prev, Out):
                self[idx - 1] = Out('%s\n%s' % (prev, cur))
                del self[idx]
            else:
                idx += 1

    def transform_strings(self, func):
        for i, atom in enumerate(self):
            if isinstance(atom, InOrOut):
                self[i] = atom.transform(func)


class InputTestCase(TestCase):
    """Blocks that contain only input entries in which o outputs should be
    computed by third parties.

    It is created by the @input and @plain decorators of the IoSpec language.
    """

    @property
    def type(self):
        return 'input'

    def __init__(self, data=(), *, inline=True, **kwds):
        super().__init__(data, **kwds)
        self.inline = inline

    def source(self):
        if all(isinstance(x, In) for x in self):
            prefix = '@plain'
        else:
            prefix = '@input'

        if self.inline:
            data = ';'.join(str(x).replace(';', '\\;').rstrip() for x in self)
            source = prefix + ' ' + data
        elif prefix == '@input':
            data = '\n'.join(('    %s' % x).rstrip() for x in self)
            source = prefix + '\n' + data
        else:
            data = '\n'.join('    %s' % x.data for x in self)
            source = prefix + '\n' + data

        return self._with_comment(source)

    def inputs(self):
        out = []
        for x in self:
            if isinstance(x, In):
                out.append(str(x))
            else:
                out.append(x.generate())
        return out


# noinspection PyMethodParameters,PyDecorator,PyArgumentList
class ErrorTestCase(TestCase):
    """
    Error test cases are created using a decorator::

        @timeout-error
            a regular block of input/output interactions

        @runtime-error
            a regular block of input/output interactions

            @error
            a block of messages displayed to stderr

        @build-error
            a regular block of input/output interactions

            @error
            a block of messages that should be displayed to stderr

        @earlytermination-error
            a regular block of input/output interactions

            @error
            a block of messages that should be displayed to stderr


    The need for error blocks is twofold. It may be the case that the desired
    behavior of a program is to indeed display an error message. It is also
    necessary in order to use the IOSpec format to *describe* how a program
    actually ran.

    The type attribute of an ErrorTestCase is one of 'error-timeout',
    'error-segfault' or 'error-exception'. In all cases, the error block
    consists of a data section that has all regular io interactions just like
    an io block and
    """

    @property
    def is_error(self):
        return True

    @property
    def type(self):
        return 'error-' + self.error_type

    def __init__(self, data=(), *,
                 error_message='', error_type='exception', **kwds):
        super().__init__(data, **kwds)
        self.error_message = str(error_message)
        self.error_type = str(error_type)

    def _factory(tt):
        @classmethod
        def method(cls, data=(), **kwds):
            if not kwds.get('error_type', tt):
                raise ValueError('invalid error_type: %r' % tt)
            kwds['error_type'] = tt
            return cls(data, **kwds)
        method.__name__ = tt
        method.__doc__ = 'Constructor for %s errors' % tt
        return method

    build = _factory('build')
    runtime = _factory('runtime')
    timeout = _factory('timeout')
    earlytermination = _factory('earlytermination')

    def source(self):
        if not self._data and not self.error_message:
            return '@%s-error\n    # Empty block' % self.error_type

        comment, self.comment = self.comment, ''
        try:
            body = data = super().source()
        finally:
            self.comment = comment

        body = '\n'.join('    ' + line for line in body.splitlines())
        if self.error_message:
            lines = self.error_message.splitlines()
            error_msg = '\n'.join('    ' + line for line in lines)
            error_msg = '\n\n    @error\n' + error_msg
        else:
            error_msg = ''

        source = '@%s-error\n%s%s' % (self.error_type, body, error_msg)
        return self._with_comment(source)

    def inputs(self):
        return IoTestCase.inputs(self)

    def transform_strings(self, func):
        super().transform_strings(func)
        self.error_message = func(self.error_message)


#
# Attribute dict
#
class AttrDict(dict):
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError

    def __setattr__(self, key, value):
        self[key] = value


#
# Comment deque
#
class CommentDeque(collections.deque):
    __slots__ = ['comment']

    def __init__(self, data=(), comment=None):
        self.comment = comment
        super().__init__(data)


class Literal(str):
    """A string-like object whose repr() is equal to str()"""

    def __repr__(self):
        return str(self)


#
# Auxiliary functions and normalizers
#
def presentation_normalizer(x):
    x.transform_strings(lambda x: x.casefold().replace(' ', '').replace('\t', ''))
    return x


def _assert_kwargs(D):
    if not _valid_kwargs.issuperset(D):
        arg = next(iter(set(D) - _valid_kwargs))
        raise TypeError('invalid argument: %s' % arg)


def normalizer(normalize=None, presentation=False):
    """Return a normalizer function that performs all given transformations."""

    L = [normalize] if normalize else []
    if presentation:
        L.append(presentation_normalizer)
    L.reverse()

    if L:
        def func(x):
            x = x.copy()

            for f in L:
                x = f(x)
            return x
        return func
    else:
        return lambda x: x

_valid_kwargs = {'presentation'}


def normalize(obj, normalize=None, **kwargs):
    """Normalize input by the given transformations.

    If a list or tuple is passed, normalize each value and return a list."""

    func = normalizer(normalize, **kwargs)

    if isinstance(obj, LinearNode):
        return func(obj)

    return [func(x) for x in obj]


@generic
def isequal(x: TestCase, y: TestCase, **kwargs):
    """Return True if both objects are equal up to some normalization."""

    x, y = normalize([x, y], **kwargs)

    if type(x) is not type(y):
        return False

    return list(x) == list(y)


@isequal.overload
def _(x: ErrorTestCase, y: ErrorTestCase, **kwargs):
    x, y = normalize([x, y], **kwargs)

    if x.error_type != y.error_type:
        return False
    if x.error_message != y.error_message:
        return False

    return isequal[TestCase, TestCase](x, y)


@isequal.overload
def _(x: IoSpec, y: IoSpec, **kwargs):
    func = normalizer(**kwargs)

    if len(x) != len(y):
        return False

    for (xi, yi) in zip (x, y):
        if not isequal(xi, yi, normalize=func):
            return False

    else:
        return True
