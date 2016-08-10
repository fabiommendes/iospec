import random

from faker import Factory

fake = Factory.create()
COMMANDS = {}


class Command:
    """
    Base class for Command objects.
    """

    def parse(self, data):
        """
        Parse content of command string.
        """

        return data

    def generate(self, argument):
        """
        Generate a new value from the parsed argument object.
        """

        return NotImplemented


class NoArgCommand(Command):
    """
    Base class for commands that do not accept arguments.
    """

    def parse(self, data):
        if data is not None:
            name = self.__class__.__name__.lower()
            raise SyntaxError('command %s do not accept arguments' % name)


def _iscommand(cls):
    """
    Register Command subclasses into the COMMANDS dict.

    This dictionary holds the default commands defined by IoSpec.
    """

    COMMANDS[cls.__name__.lower()] = cls()
    return cls


class FakerString(Command):
    """
    Base class for all commands that take a random string from faker-factory
    and return a value with some possibly maximum length.
    """

    def parse(self, size):
        if size is None:
            return None
        else:
            return int(size)

    def generate(self, argument):
        if argument is None:
            return self.fake()

        # Try to generate a valid value a few times. If we fail, we generate
        # some random name and truncate.
        size = argument
        value = None
        for _ in range(25):
            value = self.fake()
            if len(value) <= size:
                return value
        return value[:size]

    def fake(self, argument):
        raise NotImplementedError('must be overridden in subclasses')


@_iscommand
class Name(FakerString):
    """
    A random name.

        $name     --> random string with a plausible name.
        $name(xx) --> name is truncated to have at most xx characters.

    Names generated with this function usually have spaces.
    """

    def fake(self, argument):
        return fake.name()


@_iscommand
class FirstName(FakerString):
    """
    A random name.

        $firstname     --> random string with a plausible name.
        $firstname(xx) --> name is truncated to have at most xx characters.

    Names generated with this function do not have any spaces.
    """

    def fake(self, argument):
        name = ' '
        while ' ' not in name:
            name = fake.first_name()
        return name


@_iscommand
class LastName(FakerString):
    """
    A random name.

        $lastname     --> random string with a plausible name.
        $lastname(xx) --> name is truncated to have at most xx characters.

    Names generated with this function do not have any spaces.
    """

    def fake(self, argument):
        name = ' '
        while ' ' not in name:
            name = fake.last_name()
        return name


@_iscommand
class Fake(Command):
    """
    Return a random fake data.

    Any method from Python's fake-factory package is accepted.

    Example:

        $fake(email) --> return a random e-mail.
    """

    def parse(self, attr):
        blacklist = [
            'add_provider', 'format', 'get_formatter', 'get_providers' 'parse',
            'provider', 'providers', 'set_formatter',
        ]
        if attr.startswith('_') or attr not in dir(fake) or attr in blacklist:
            raise SyntaxError('invalid fake method: %s' % attr)

    def generate(self, argument):
        return getattr(fake, argument)()


@_iscommand
class Str(FakerString):
    """
    A random string.

        $str     --> random string of text.
        $str(xx) --> string is truncated to have at most xx characters.

    Strings generated with this function do not have any new lines.
    """

    def fake(self, argument):
        data = '\n'
        while '\n' not in data:
            data = fake.pystr()
        return data


@_iscommand
class Text(FakerString):
    """
    A random string.

        $text     --> random string of text.
        $text(xx) --> string is truncated to have at most xx characters.

    Strings generated with this function have new lines separating paragraphs.
    """

    def fake(self, argument):
        return '\n\n'.join(fake.paragraphs())


@_iscommand
class Paragraph(FakerString):
    """
    A random string.

        $paragraph     --> random paragraph with multiple sentences.
        $paragraph(xx) --> string is truncated to have at most xx characters.

    Strings generated with this function do not have new lines.
    """

    def fake(self, argument):
        return fake.paragraph()


@_iscommand
class Int(Command):
    """
    A random integer. This command have many different signatures used to
    generate different intervals

        $int       --> any random integer
        $int(+)    --> positive random value (zero inclusive)
        $int(-)    --> negative value (zero inclusive)
        $int(++)   --> positive value (do not include zero)
        $int(--)   --> negative value (do not include zero)
        $int(+a)   --> positive values up to "a" (include zero)
        $int(-a)   --> negative values up to "a" (include zero)
        $int(++a)  --> positive values up to "a" (do not include zero)
        $int(--a)  --> negative values up to "a" (do not include zero)
        $int(a)    --> symmetric interval (-a, a)
        $int(a,b)  --> interval (a, b) (inclusive)
        $int(a..b) --> same as before
        $int(a:b)  --> interval a to b - 1. Like a Python range.

    """
    def parse(self, arg):
        return parse_number(arg, int)

    def generate(self, argument):
        return random.randint(*argument)


@_iscommand
class Float(Command):
    """
    Any random floating point number.

    Accept the same arguments as integers.
    """

    def parse(self, arg):
        return parse_number(arg, float, minvalue=-2 ** 50, maxvalue=2 ** 50)

    def generate(self, argument):
        return random.uniform(*argument)


@_iscommand
class Digit(NoArgCommand):
    """
    A one digit number.
    """

    def generate(self, argument):
        return random.randint(0, 9)


@_iscommand
class SmallFloat(NoArgCommand):
    """
    A small floating point number between zero and one.
    """

    def generate(self, argument):
        return random.uniform(0, 1)


class Foo(Command):
    """
    A simple echoing command useful for testing. This name is not exported
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


#
# Auxiliary functions
#
def parse_number(arg, number_class, minvalue=-2 ** 31, maxvalue=2 ** 31 - 1):
    """
    Parse a string of text that represents a valid numeric range.

    The syntax is:
             ==> (minvalue, maxvalue)
        +    ==> (0, maxvalue)
        -    ==> (minvalue, 0)
        ++   ==> (1, maxvalue)
        --   ==> (minvalue, -1)
        +a   ==> (0, a)
        -a   ==> (-a, 0)
        a    ==> (-a, a)
        a..b ==> (a, b)
        a,b  ==> (a, b)
        a:b  ==> (a, b-1)
    """

    arg = arg.strip()

    try:
        if not arg:
            pass
        elif arg == '+':
            minvalue = 0
        elif arg == '-':
            maxvalue = 0
        elif arg == '++':
            minvalue = 1
        elif arg == '--':
            maxvalue = -1
        elif arg.startswith('-'):
            maxvalue = 0
            minvalue = -number_class(arg[1:])
        elif arg.startswith('+'):
            minvalue = 0
            maxvalue = number_class(arg[1:])
        elif arg.startswith('--'):
            maxvalue = -1
            minvalue = -number_class(arg[2:])
        elif arg.startswith('++'):
            minvalue = 1
            maxvalue = number_class(arg[2:])

        elif '..' in arg:
            min, _, max = arg.partition('..')
            minvalue = number_class(min)
            maxvalue = number_class(max)
        elif ':' in arg:
            min, _, max = arg.partition(':')
            minvalue = number_class(min)
            maxvalue = number_class(max) - 1
        elif ',' in arg:
            min, _, max = arg.partition(',')
            minvalue = number_class(min)
            maxvalue = number_class(max)
        else:
            maxvalue = number_class(arg)
            minvalue = -maxvalue
    except ValueError:
        raise SyntaxError('invalid interval specification: %s' % arg)

    return (minvalue, maxvalue)


#
# Utility functions
#
class _wrapped(Command):
    """
    A wrapped command factory function that has the same interface as a Command
    instance.
    """
    def __init__(self, func):
        self.func = func

    def generate(self, arg):
        return self.func(arg)

    def __repr__(self):
        return '<wrapped %s() function>' % getattr(self.func, '__name__', '?')


def wrapped_command(obj):
    """
    Wraps a functional command into class instance when necessary
    """

    if isinstance(obj, type):
        if not hasattr(obj, 'parse') or not hasattr(obj, 'generate'):
            raise ValueError('class must define a generate() and a parse() '
                             'methods')
        return obj()
    else:
        return _wrapped(obj)
