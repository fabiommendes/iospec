from iospec.datatypes.node import Node
from iospec.datatypes.utils import AttrDict


class IoSpec(Node):
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

    type = 'iospec'

    @property
    def has_errors(self):
        from iospec.datatypes import ErrorTestCase

        return any(isinstance(x, ErrorTestCase) for x in self)

    @property
    def is_simple(self):
        return all(x.is_simple for x in self)

    @property
    def is_expanded(self):
        return all(x.is_expanded for x in self)

    @classmethod
    def from_json(cls, data):
        """
        Decode JSON representation of IoSpec data.
        """

        from iospec.datatypes import TestCase

        return cls([TestCase.from_json(x) for x in data])

    def __init__(self, data=(), *, commands=None, definitions=None):
        super().__init__(data)
        self.commands = AttrDict(commands or {})
        self.definitions = []
        self.definitions.extend(definitions or ())

    def __repr__(self):
        type_name = type(self).__name__
        return '<%s: %s>' % (type_name, [x.type for x in self])

    def source(self):
        prefix = '\n\n'.join(block.strip('\n') for block in self.definitions)

        data = []
        for idx, case in enumerate(self):
            # Join consecutive inline blocks
            if case.is_input and case.inline and idx:
                prev = self[idx - 1]
                if prev.is_input and prev.inline:
                    data[-1] += '\n' + case.source()
                    continue

            data.append(case.source())

        return prefix + '\n\n'.join(data)

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
                return case.error_type

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

    def _normalize_trailing_spaces(self):
        for x in self:
            x._normalize_trailing_spaces()

    def _normalize_in_out_strings(self):
        for x in self:
            x._normalize_in_out_strings()

    def _normalize_in_out_streams(self):
        for x in self:
            x._normalize_in_out_streams()

    def _join_out_strings(self):
        for x in self:
            x._join_out_strings()

    def _convert_item(self, item):
        from iospec.datatypes import TestCase

        if not isinstance(item, TestCase):
            raise TypeError('invalid item: %r' % item)
        return item
