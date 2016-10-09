from iospec.datatypes import Command, In, Out, Atom, OutEllipsis, OutRegex
from iospec.datatypes.node import Node
from iospec.datatypes.utils import isequal
from iospec.exceptions import BuildError
from iospec.utils import indent


class TestCase(Node):
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
    def is_input(self):
        return isinstance(self, InputTestCase)

    @property
    def is_expanded(self):
        return all(x.is_expanded for x in self)

    @property
    def is_safe(self):
        return all(x.is_safe for x in self)

    @property
    def is_complete(self):
        return (not self.is_input) and all(x.is_complete for x in self)

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

    def __init__(self, data=(), *, priority=None, lineno=None, **kwds):
        if self.__class__ is TestCase:
            raise TypeError('cannot instantiate abstract TestCase instance')

        super().__init__(data, **kwds)
        self._priority = priority
        self.lineno = lineno

    def inputs(self):
        """
        Return a list of inputs for the test case.
        """

        values = []
        for x in self:
            if isinstance(x, In):
                values.append(str(x))
            elif isinstance(x, Command):
                values.append(x.generate())
            elif getattr(x, 'is_output', False):
                pass
            else:
                raise ValueError('invalid input object: %r' % x)
        return values

    def expand_inputs(self):
        """
        Expand all computed input nodes *INPLACE*.
        """

        for idx, atom in enumerate(self):
            if isinstance(atom, Command):
                self[idx] = atom.expand()

    def fuse_outputs(self, sep='\n'):
        """
        Fuse Out strings together.
        """

        idx = 1
        while idx < len(self):
            cur = self[idx]
            prev = self[idx - 1]
            if isinstance(cur, Out) and isinstance(prev, Out):
                self[idx - 1] = Out(str(prev) + sep + str(cur))
                del self[idx]
            else:
                idx += 1

    def source(self):
        data = ''.join(x.source() for x in self if x != Out(''))
        return self._with_comment(data)

    def transform_strings(self, func):
        for i, atom in enumerate(self):
            if isinstance(atom, (In, Out, OutEllipsis)):
                self[i] = atom.transform(func)

    def get_testcase(self):
        return self.copy()

    def get_error_message(self):
        return ''

    def get_exception(self):
        return None

    def raise_exception(self):
        raise Exception('raising exception from non-error test case')

    def _join_out_strings(self):
        self.fuse_outputs()

    def _normalize_in_out_strings(self):
        if len(self) == 0:
            self.append(Out(''))

        new_data = [] if self[0].is_output else [Out('')]
        is_input = not bool(new_data)
        for atom in self:
            if is_input and atom.is_input:
                new_data.append(Out(''))
            new_data.append(atom)
            is_input = atom.is_input

        if len(new_data) != len(self):
            self[:] = new_data

    def _normalize_in_out_streams(self):
        # Nothing to do in normalized content
        if len(self) == 2 and self[0].is_input and self[1].is_output:
            return

        data = [x for x in self if x.is_input]
        out = [x for x in self if not x.is_input]
        if not out:
            out = [Out('')]
        data.extend(out)
        self[:] = data
        self.fuse_outputs(sep='')

        if isinstance(self[-1], (Out, OutEllipsis)) and self[-1].endswith('\n'):
            self[-1] = self[-1].strip('\n')

    def _normalize_trailing_spaces(self):
        # Detect trailing spaces inside string
        for idx, atom in enumerate(self):
            if isinstance(atom, (Out, OutEllipsis)):
                data = new = str(atom)
                if '\n' in data:
                    lines = data.splitlines()
                    new = [x.rstrip() for x in lines[:-1]]
                    new.append(lines[-1])
                    new = '\n'.join(new)
                if data != new:
                    self[idx] = type(atom)(new)

        # Last output string cannot have a trailing space
        if len(self) and isinstance(self[-1], (Out, OutEllipsis)):
            atom = self[-1]
            data = str(atom)
            if data != data.rstrip():
                self[-1] = type(atom)(data.rstrip())

    def _convert_item(self, item):
        if isinstance(item, Atom):
            return item
        raise TypeError('invalid test case item: %r' % item)


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

    def __init__(self, data=(), *, inline=True, **kwargs):
        plain = kwargs.pop('plain', None)
        super().__init__(data, **kwargs)
        self.inline = inline

        if plain is None:
            self.plain = all(isinstance(x, In) for x in self)
        else:
            self.plain = bool(plain)

    def source(self):
        if self.plain:
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

    def _normalize_in_out_strings(self):
        pass

    def _normalize_in_out_streams(self):
        pass

    def _normalize_trailing_spaces(self):
        pass

    def _join_out_strings(self):
        pass

    def _convert_item(self, item):
        if isinstance(item, str):
            return In(item)
        return super()._convert_item(item)


class ErrorTestCase(TestCase):
    """
    Error test cases check if a program fails in some specific way. It is also
    necessary in order to use the IoSpec format to *describe* how a program
    actually ran, in case execution triggers an error.
    """

    def error_test_case_constructor(tt):
        def method(cls, data=(), **kwds):
            if not kwds.get('error_type', tt):
                raise ValueError('invalid error_type: %r' % tt)
            kwds['error_type'] = tt
            return cls(data, **kwds)

        method.__name__ = tt
        method.__doc__ = 'Constructor for %s errors' % tt
        return classmethod(method)

    build = error_test_case_constructor('build')
    timeout = error_test_case_constructor('timeout')
    runtime = error_test_case_constructor('runtime')
    del error_test_case_constructor

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
            case = self.get_testcase()
            source = case.source()
            return self._with_comment('@timeout-error\n' + indent(source, 4))

    def _source_runtime(self):
        error_msg = self.error_message
        error_msg = indent(error_msg, 4)
        if len(self) == 0:
            return self._with_comment('@timeout-error\n@error\n' + error_msg)

        else:
            case = self.get_testcase()
            source = case.source()
            data = '@runtime-error\n' + indent(source, 4)
            if self.error_message:
                data += '\n\n@error\n' + error_msg
            return self._with_comment(data)

    def transform_strings(self, func):
        super().transform_strings(func)
        self.error_message = func(self.error_message)

    def get_testcase(self):
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


#
# Utility functions
#
@isequal.overload
def _(x: ErrorTestCase, y: ErrorTestCase, **kwargs):
    if x.error_type != y.error_type:
        return False
    if x.error_message != y.error_message:
        return False

    return isequal[TestCase, TestCase](x, y)
