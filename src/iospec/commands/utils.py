from iospec.commands.base import Command

COMMANDS_NAMESPACE = {}


def number(x):
    """
    Convert string to number.
    """

    try:
        return int(x)
    except ValueError:
        return float(x)


def iscommand(cls):
    """
    Register Command subclasses into the COMMANDS dict.

    This dictionary holds the default commands defined by IoSpec.
    """

    COMMANDS_NAMESPACE[cls.__name__.lower()] = cls
    return cls


def parse_number(arg, number_class, minvalue=-1000000, maxvalue=1000000):
    """
    Parse a string of text that represents a valid numeric range.

    The syntax is:
             ==> (minvalue, maxvalue)
        a    ==> (0, a)
        -a   ==> (-a, 0)
        a,b  ==> (a, b)
    """

    arg = (arg or '').strip()

    # Empty argument
    if not arg:
        return (minvalue, maxvalue)

    # Interval
    if ',' in arg:
        x, y = arg.split(',')
        x, y = number(x), number(y)
        if x > y:
            raise ValueError('first argument is greater then second')
        return x, y

    # Number
    value = number(arg)
    if value >= 0:
        return 0, value
    else:
        return value, 0


def wrapped_command(cmd):
    """
    Wraps a functional command into class instance when necessary
    """

    if isinstance(cmd, type):
        if not hasattr(cmd, 'parse') or not hasattr(cmd, 'generate'):
            raise ValueError('class must define a generate() and a parse() '
                             'methods')
        return cmd()
    else:
        function = cmd

        class wrapped(Command):
            """
            A wrapped command factory function that has the same interface as a
            Command instance.
            """

            def __init__(self, arg=''):
                self.arg = arg

            def parse(self, arg):
                self.arg = arg

            def generate(self):
                return function(self.arg)

            def __repr__(self):
                return '<wrapped %s() function>' % getattr(self.func,
                                                           '__name__', '?')

        return wrapped()
