import collections
import copy
import pprint


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

    def normalize(self):
        """
        Normalize Iospec element *INPLACE* to have a predictable structure.

        By default, make the following fixes:

        * Remove trailing spaces from outputs
        * Alternate Out/In strings in SimpleTestCase nodes.
        * Join consecutive Out strings putting newlines between them.
        """

        self._join_out_strings()
        self._normalize_trailing_spaces()
        self._normalize_in_out_strings()

    def _normalize_trailing_spaces(self):
        pass

    def _normalize_in_out_strings(self):
        pass

    def _join_out_strings(self):
        pass

    def _convert_item(self, item):
        return item
