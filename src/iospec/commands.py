#
# All builtin computed input commands
#
import string
import random

__all__ = ['COMMANDS']
COMMANDS = {}


class _wrapped:
    def __init__(self, func):
        self.func = func

    def parse(self, arg):
        return arg

    def generate(self, arg):
        return self.func(arg)

    def __repr__(self):
        return '<wrapped %s() function>' % getattr(self.func, '__name__', '?')


def wrapped_command(obj):
    """Wraps a functional command in class when necessary"""

    if isinstance(obj, type):
        if not hasattr(obj, 'parse') or not hasattr(obj, 'generate'):
            raise ValueError('class must define a generate() and a parse() '
                             'methods')
        return obj()
    else:
        return _wrapped(obj)


# Register commands into the commands dict
def iscommand(cls):
    COMMANDS[cls.__name__.lower()] = cls()
    __all__.append(cls.__name__)
    return cls


@iscommand
class Name:
    def parse(self, size):
        return int(size or '20')

    def generate(self, value):
        self.init()
        return self.generate_new(value)

    def generate_new(self, size):
        choice = random.choice
        L = string.ascii_letters
        return ''.join(choice(L) for _ in range(size))

    @classmethod
    def init(cls):
        # Create a list of precomputed names (maybe cache in a serialized
        # pickle)
        if getattr(cls, '_hasinit', False):
            return

        cls.words = {
            1: string.ascii_letters,
            2: ['fo', 'ba'],
            # ...
        }
        cls._hasinit = True


@iscommand
class FullName:
    def parse(self, arg):
        pass

    def generate(self, value):
        pass


@iscommand
class Str:
    def parse(self, arg):
        pass

    def generate(self, value):
        pass


@iscommand
class Text:
    def parse(self, arg):
        pass

    def generate(self, value):
        pass


@iscommand
class Int:
    def parse(self, arg):
        pass

    def generate(self, value):
        pass


@iscommand
class Float:
    def parse(self, arg):
        pass

    def generate(self, value):
        pass


# noinspection PyUnresolvedReferences
class Foo:
    """A simple echoing command useful for testing. This name is not exported
    to the default commands dictionary but can be inserted on any parse tree
    by setting

    >>> parse_tree(source, commands={'foo': Foo()})             # doctest: +SKIP

    The Foo command expands to the string "foo" or a repetition such as
    $foo(2) --> "foofoo"
    """

    def parse(self, args):
        return int(args or '1')

    def generate(self, n):
        return 'foo' * n
