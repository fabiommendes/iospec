from generic import generic
from iospec.datatypes.node import Node


def normalize(obj, normalize=None, **kwargs):
    """
    Normalize input by the given transformations.

    If a list or tuple is passed, normalize each value and return a list.
    """

    func = normalizer(normalize, **kwargs)

    if isinstance(obj, Node):
        return func(obj)

    return [func(x) for x in obj]


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


@generic
def isequal(x, y, **kwargs):
    """
    Return True if two objects are equal up to some normalization.
    """
    return x == y
