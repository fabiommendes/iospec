import collections
import copy
import pprint
import re

from generic import generic
from unidecode import unidecode

from iospec.exceptions import BuildError
from iospec.utils import indent

__all__ = [
    # Atomic
    'Atom', 'Comment', 'In', 'Out', 'Command', 'OutEllipsis', 'OutRegex',

    # Nodes
    'IoSpec', 'TestCase', 'ErrorTestCase', 'SimpleTestCase', 'InputTestCase',

    # Functions
    'isequal', 'normalize'
]


class Atom(collections.UserString):
    """Base class for all atomic elements"""

    escape_chars = {
        '<': '\\<',
        '$': '\\$',
        '...': '\\...',
    }

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

    type = 'comment'

    def source(self):
        return self.data

    def content(self):
        return '\n'.join(line[1:] for line in self.data.splitlines() if line)


class InOrOut(Atom):
    """Common interfaces to In and Out classes"""

    ELLIPSIS_MATCH = re.compile(r'(?:^\.\.\.|[^\\]\.\.\.)')

    def __init__(self, data, fromsource=False, lineno=None):
        if fromsource:
            data = self._un_escape(data)
        super().__init__(data, lineno=lineno)


class In(InOrOut):
    """Plain input string"""

    type = 'input'

    def source(self):
        return '<%s>\n' % super().source()


class OutOrEllipsis(InOrOut):
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
    """Plain output string"""

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


#
# Container nodes for the iospec AST
#
class LinearNode(collections.MutableSequence):
    """
    We call a single interaction/run of a program with a set of user inputs
    a "test case".

    There are different types of case nodes, either "error-*", for representing
    failed executions, "input-*" for representing input-only specifications and
    finally "io-*", that represents both inputs and outputs of a successful
    program run.
    """

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
        """
        JSON-like expansion of the AST.

        All linear node instances are expanded into dictionaries.
        """

        dic = {'type': getattr(self, 'type', type(self).__name__)}
        dic.update(vars(self))

        # Hide default values
        for key in ['lineno', 'comment', 'meta']:
            if key in dic and not dic[key]:
                del dic[key]

        # Rename private attributes
        dic['data'] = dic.pop('_data')
        for k in ['priority', 'error']:
            if '_' + k in dic:
                dic[k] = value = dic.pop('_' + k)
                if not value:
                    del dic[k]

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

        return {k: json(v) for (k, v) in dic.items()}

    def copy(self):
        """Return a deep copy."""

        return copy.deepcopy(self)

    def set_meta(self, attr, value):
        """Writes an attribute of meta information."""

        self.meta[attr] = value

    def get_meta(self, attr, *args):
        """
        Retrieves an attribute of meta information.

        Can give a second positional argument with the default value to return
        if the attribute does not exist.
        """

        if args:
            return self.meta.get(attr, args[0])

        try:
            return self.meta[attr]
        except KeyError:
            raise AttributeError('invalid meta attribute: %r' % attr)

    def transform_strings(self, func):
        """
        Transform all visible string values in test case by the given function
        *inplace*.
        """

        for case in self:
            case.transform_strings(func)


# noinspection PyUnresolvedReferences
class IoSpec(LinearNode):
    """
    Root node of an iospec AST.

    Args:
        data (seq):
            A (possibly empty) sequence of test cases.
        commands (dict):
            A mapping of command names to their respective functions or Command
            subclasses.
        definitions (list):
            A list of command definitions declared in the IoSpec source.

    Attributes:
        has_errors (bool):
            True if IoSpec structure has an ErrorTestCase child.
        is_simple (bool):
            True if all children are instances of SimpleTestCase.
        is_expanded (bool):
            True if all children are instances of SimpleTestCase that have all
            input commands expanded. This tells that each child is made of just
            a sequence of :class:`In` and :class:`Out` strings.
    """

    @property
    def has_errors(self):
        return any(isinstance(x, ErrorTestCase) for x in self)

    @property
    def is_simple(self):
        return all(x.is_simple for x in self)

    @property
    def is_expanded(self):
        return all(x.is_expanded for x in self)

    def __init__(self, data=(), *, commands=None, definitions=None):
        super().__init__(data)
        self.commands = AttrDict(commands or {})
        self.definitions = []
        self.definitions.extend(definitions or ())

    def __repr__(self):
        type_name = type(self.__class__.__name__)
        return '<%s: %s>' % (type_name, [x.type for x in self])

    def source(self):
        prefix = '\n\n'.join(block.strip('\n') for block in self.definitions)
        return prefix + '\n\n'.join(case.source() for case in self)

    def inputs(self):
        """
        Return a list of lists of input strings.
        """

        return [x.inputs() for x in self]

    def expand_inputs(self, size=0):
        """
        Expand all input command nodes into regular In() atoms.

        The changes are done *inplace*.


        Args:
            size
                The target size for the total number of test cases. If the tree
                has less test cases than size, it will create additional test
                cases according to the test case priority.
        """

        if size < len(self):
            for case in self:
                case.expand_inputs()
        else:
            # Expand to reach len(self) == size
            diff = size - len(self)
            if not diff:
                return
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
        """
        Fuse consecutive Out() strings together *inplace*.
        """

        for case in self:
            case.fuse_outputs()

    def get_exception(self):
        """
        Return an exception instance that describes the first error encountered
        in the run.

        If no errors are found, return None.
        """

        for case in self:
            if case.is_error:
                return case.get_exception()

    def get_error_type(self):
        """
        Return a string with the first error type encountered in the IoSpec.

        If no errors are found, return None.
        """

        for case in self:
            if case.is_error:
                return case.get_error_type()

    def get_error_message(self):
        """
        Return a string with the first error message encountered in the IoSpec.

        If no errors are found, return None.
        """

        for case in self:
            if case.is_error:
                return case.get_error_message()

    def to_json(self):
        """
        Convert object to a json structure.
        """

        return [x.to_json() for x in self]

    @classmethod
    def from_json(cls, data):
        """
        Decode JSON representation of IoSpec data.
        """

        return cls([TestCase.from_json(x) for x in data])


class TestCase(LinearNode):
    """
    Base class for all test cases.

    Args:
        data:
            A sequence of In, Out and Command strings.
        priority (float):
            Relative priority of this test case for input expansion.
        lineno (int):
            The line number for this test case in the IoSpec source.
    """

    @property
    def type(self):
        return self.__class__.__name__.lower()[:-8]

    # noinspection PyArgumentList
    def __init__(self, data=(), *, priority=None, lineno=None, **kwds):
        if self.__class__ is TestCase:
            raise TypeError('cannot instantiate abstract TestCase instance')

        super().__init__(data, **kwds)
        self._priority = priority
        self.lineno = lineno


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
        return isinstance(self, ErrorTestCase)

    @property
    def is_simple(self):
        return isinstance(self, SimpleTestCase)

    @property
    def is_expanded(self):
        io_types = {In, Out}
        return self.is_simple and set(map(type, self)).issubset(io_types)

    @property
    def is_input(self):
        return isinstance(self, InputTestCase)

    def inputs(self):
        """
        Return a list of inputs for the test case.
        """

        return [str(x) for x in self if isinstance(x, In)]

    def expand_inputs(self):
        """
        Expand all computed input nodes *inplace*.
        """

        for idx, atom in enumerate(self):
            if isinstance(atom, Command):
                self[idx] = atom.expand()

    def fuse_outputs(self):
        """
        Fuse Out strings together.
        """

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

    def to_json(self):
        return {'type': self.__class__.__name__.lower()[:-8],
                'data': [x.to_json() for x in self]}

    @classmethod
    def from_json(cls, data):
        json = dict(data)
        type_name = json.pop('type')
        atoms = [Atom.from_json(x) for x in json.pop('data')]
        if type_name == 'simple':
            result = SimpleTestCase(atoms)
        elif type_name == 'input':
            result = InputTestCase(atoms)
        elif type_name == 'error':
            result = ErrorTestCase(
                atoms,
                error_message=json.pop('error_message', ''),
                error_type=json.pop('error_type', 'runtime'),
            )
        else:
            raise ValueError('invalid type: %r' % type_name)
        if json:
            raise ValueError('invalid parameter: %s=%r' % json.popitem())
        return result


class SimpleTestCase(TestCase):
    """
    Regular input/output test case.
    """


class InputTestCase(TestCase):
    """
    Blocks that contain only input entries in which o outputs should be
    computed by third parties.

    It is created by the @input and @plain decorators of the IoSpec language.
    """

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
            elif isinstance(x, Command):
                out.append(x.generate())
            else:
                raise ValueError('invalid input object: %r' % x)
        return out

    def to_json(self):
        data = []
        for st in self:
            try:
                data.append(st.to_json())
            except AttributeError:
                data.append(['In', st])

        return {'type': 'input', 'data': data}


#
# Factory function for the ErrorTestCase.{build, runtime, timeout} functions
#
def _error_test_case_constructor_factory(tt):
    def method(cls, data=(), **kwds):
        if not kwds.get('error_type', tt):
            raise ValueError('invalid error_type: %r' % tt)
        kwds['error_type'] = tt
        return cls(data, **kwds)

    method.__name__ = tt
    method.__doc__ = 'Constructor for %s errors' % tt
    return classmethod(method)


class ErrorTestCase(TestCase):
    """
    Error test cases are created using a decorator::

        @runtime-error
            The main body has a regular block of input/output interactions.

            This error describes the most common case of failure: when an error
            is triggered during a program execution. Errors can be anything from
            seg-faults to exceptions, or buffer overflows, etc.

            @error
                optional block of messages displayed to stderr


        @timeout-error
            The main body has a regular block of input/output interactions.

            Timeout errors happen when execution takes longer than expected.
            It doesn't define an error message since the program did not fail,
            but the runner decided to terminate its execution.


        @build-error
            The main body has a block of messages that should be displayed to
            stderr. Build errors cannot have a regular block of IO interactions
            since they happen prior to program execution.

            Build errors happen when program is being prepared to execute. Can
            be a syntax error, compilation error or anything that prevents
            the program to run.


    Error test cases check if a program fails in some specific way. It is also
    necessary in order to use the IOSpec format to *describe* how a program
    actually ran, in case an error is found.
    """

    build = _error_test_case_constructor_factory('build')
    timeout = _error_test_case_constructor_factory('timeout')
    runtime = _error_test_case_constructor_factory('runtime')

    def __init__(self, data=(), *,
                 error_message='', error_type='runtime', **kwds):
        super().__init__(data, **kwds)
        self.error_message = error_message or ''
        self.error_type = error_type

        # Check parameters consistency
        if self.error_type not in ['timeout', 'runtime', 'build']:
            raise ValueError('invalid error type: %s' % self.error_type)
        if self.error_type == 'build' and data:
            raise ValueError('build errors must have an empty data argument')
        if self.error_type == 'timeout' and self.error_message:
            raise ValueError('timeout errors do not have an associated error '
                             'message.')

    def to_json(self):
        json = super().to_json()
        json['error_type'] = self.error_type
        if self.error_message:
            json['error_message'] = self.error_message
        return json

    def source(self):
        if self.error_type == 'build':
            return self._source_build()
        elif self.error_type == 'timeout':
            return self._source_timeout()
        elif self.error_type == 'runtime':
            return self._source_runtime()
        raise RuntimeError

    def _source_build(self):
        msg = self.error_message
        return self._with_comment('@build-error\n' + indent(msg, 4))

    def _source_timeout(self):
        if len(self) == 0:
            return self._with_comment('@timeout-error\n')
        else:
            case = self.get_test_case()
            source = case.source()
            return self._with_comment('@timeout-error\n' + indent(source, 4))

    def _source_runtime(self):
        error_msg = self.error_message
        error_msg = indent(error_msg, 4)
        if len(self) == 0:
            return self._with_comment('@timeout-error\n@error\n' + error_msg)

        else:
            case = self.get_test_case()
            source = case.source()
            data = '@runtime-error\n' + indent(source, 4)
            if self.error_message:
                data += '\n\n@error\n' + error_msg
            return self._with_comment(data)

    def transform_strings(self, func):
        super().transform_strings(func)
        self.error_message = func(self.error_message)

    def get_test_case(self):
        """
        Return a SimpleTestCase() instance with the same data in the test case
        section of the error.

        Build errors do not have an test case section and raise a ValueError.
        """

        if self.error_type == 'build':
            raise ValueError('build errors have no test case section')

        return SimpleTestCase(list(self))

    def get_error_message(self):
        """
        Return a friendly error message.
        """

        if self.error_type == 'timeout':
            return 'TimeoutError: program exceeded timeout.'
        if self.error_message:
            return self.error_message
        elif self.error_type == 'build':
            return 'BuildError: could not build/compile program.'
        elif self.error_type == 'runtime':
            return 'RuntimeError: error during program execution.'
        else:
            raise ValueError('invalid error type: %r' % self.error_type)

    def get_exception(self):
        """
        Return an exception instance associated with the error.
        """

        if self.error_type == 'timeout':
            return TimeoutError()
        elif self.error_type == 'build':
            return BuildError(self.error_message)
        elif self.error_type == 'runtime':
            return RuntimeError(self.error_message)

    def raise_exception(self):
        """
        Raise exception associated with ErrorTestCase.
        """

        raise self.get_exception()


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


class CommentDeque(collections.deque):
    """
    A deque with a .comment string attribute.
    """
    __slots__ = ['comment']

    def __init__(self, data=(), comment=None):
        self.comment = comment
        super().__init__(data)


class Literal(str):
    """
    A string-like object whose repr() is equal to str().
    """

    def __repr__(self):
        return str(self)


def presentation_normalizer(x):
    """
    Normalize TestCase object to detect presentation errors.
    """
    x.transform_strings(
        lambda x: x.casefold().replace(' ', '').replace('\t', ''))
    return x


def normalizer(normalize=None, presentation=False):
    """
    Return a normalizer function that performs all given transformations.
    """

    lst = [normalize] if normalize else []
    if presentation:
        lst.append(presentation_normalizer)
    lst.reverse()

    if lst:
        def func(x):
            x = x.copy()

            for f in lst:
                x = f(x)
            return x

        return func
    else:
        return lambda x: x


def normalize(obj, normalize=None, **kwargs):
    """
    Normalize input by the given transformations.

    If a list or tuple is passed, normalize each value and return a list.
    """

    func = normalizer(normalize, **kwargs)

    if isinstance(obj, LinearNode):
        return func(obj)

    return [func(x) for x in obj]


@generic
def isequal(x: TestCase, y: TestCase, **kwargs):
    """
    Return True if both objects are equal up to some normalization.
    """

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

    for (xi, yi) in zip(x, y):
        if not isequal(xi, yi, normalize=func):
            return False
    else:
        return True
