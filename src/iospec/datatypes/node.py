import collections
import copy
import pprint
import re

from iospec.datatypes.utils import isequal


class Node(collections.MutableSequence):
    """
    Base class for IoSpec and TestCase objects.
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
        if isinstance(idx, (int, slice)):
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
        if isinstance(i, int):
            self._data[i] = self._convert_item(value)
        else:
            convert = self._convert_item
            data = [convert(x) for x in value]
            self._data[i] = data

    def __delitem__(self, i):
        del self._data[i]

    def __repr__(self):
        return super().__repr__()

    def __eq__(self, other):
        if type(self) is type(other):
            return self.isequal(other)
        return NotImplemented

    def source(self):
        """
        Render AST node as iospec source code.
        """

        data = ''.join(x.source() for x in self)
        return self._with_comment(data)

    def _with_comment(self, data):
        if self.comment:
            return '%s\n%s' % (self.comment, data)
        return data

    def insert(self, idx, value):
        value = self._convert_item(value)
        self._data.insert(idx, None)
        try:
            self._data[idx] = value
        except:
            del self._data[idx]
            raise

    def pformat(self, *args, **kwds):
        """
        Format AST in a pprint-like format.
        """

        return pprint.pformat(self.to_json(), *args, **kwds)

    def pprint(self, *args, **kwds):
        """
        Pretty print AST.
        """

        print(self.pformat(*args, **kwds))

    def to_json(self):
        """
        JSON-like expansion of the AST.

        All linear node instances are expanded into dictionaries.
        """

        def to_json(x):
            if hasattr(x, 'to_json'):
                return x.to_json()

            if isinstance(x, (list, tuple)):
                return [to_json(y) for y in x]
            elif isinstance(x, dict):
                return {k: to_json(v) for (k, v) in x.items()}
            else:
                return x

        # Data and type
        dic = {
            'type': getattr(self, 'type', self.__class__.__name__.lower()),
            'data': to_json(self._data),
        }

        # Meta variables
        for key in ['lineno', 'comment', 'meta']:
            value = getattr(self, key, None)
            if value:
                dic[key] = to_json(value)

        return {k: to_json(v) for (k, v) in dic.items()}

    def copy(self):
        """
        Return a deep copy.
        """

        return copy.deepcopy(self)

    def set_meta(self, attr, value):
        """
        Writes an attribute of meta information.
        """

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
        *INPLACE*.
        """

        for case in self:
            case.transform_strings(func)

    def casefold(self):
        """
        Convert all strings to a normalized lowercase *INPLACE*.
        """

        self.transform_strings(lambda x: x.casefold())
    
    def skip_spaces(self):
        """
        Remove all extra repeated spaces from strings. *INPLACE*.
        """

        regex = re.compile('\s+')

        def skip_spaces(x):
            data = str(x).strip()
            return ' '.join(regex.split(data))

        self.transform_strings(skip_spaces)

    def normalize(self, stream=False):
        """
        Normalize Iospec element *INPLACE* to have a predictable structure.

        By default, make the following fixes:

        * Remove trailing spaces from outputs
        * Alternate Out/In strings in SimpleTestCase nodes.
        * Join consecutive Out strings putting newlines between them.

        If ``stream=True``, normalize to a C-like interaction: all inputs are
        moved to the beginning and all outputs are fused in the end of file.
        This is useful to compare interactions from C programs or from other
        languages that interact directly with low level stdout/stdin/stderr
        streams.
        """

        if stream:
            self._normalize_in_out_streams()
        else:
            self._join_out_strings()
            self._normalize_trailing_spaces()
            self._normalize_in_out_strings()

    def isequal(self, other, normalize=True, casefold=False, skip_spaces=False):
        """
        Test if object is equal to argument.

        The default equality test is implemented as x.isequal(y). This function
        gives better control over equality tests.

        Args:
            normalize (bool):
                If True (default), apply x.normalize() data before comparison.
            casefold (bool):
                If True, convert all strings to lowercase.
            skip_spaces (bool):
                If True, skips all spaces in input and output strings.
        """

        return isequal(self, other,
                       normalize=normalize,
                       casefold=casefold,
                       skip_spaces=skip_spaces)

    def _normalize_trailing_spaces(self):
        pass

    def _normalize_in_out_strings(self):
        pass

    def _normalize_in_out_streams(self):
        pass

    def _join_out_strings(self):
        pass

    def _convert_item(self, item):
        return item


@isequal.overload
def _(x: Node, y: Node, normalize=True, casefold=False, skip_spaces=False):
    if not (isinstance(x, type(y)) or isinstance(y, type(x))):
        return False

    if normalize or casefold or skip_spaces:
        x = x.copy()
        y = y.copy()

    if normalize:
        x.normalize()
        y.normalize()

    if casefold:
        x.casefold()
        y.casefold()

    if skip_spaces:
        x.skip_spaces()
        y.skip_spaces()

    return list(x) == list(y)