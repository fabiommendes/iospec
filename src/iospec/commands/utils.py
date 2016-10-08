from iospec.commands.base import Command

COMMANDS_NAMESPACE = {}


def iscommand(cls):
    """
    Register Command subclasses into the COMMANDS dict.

    This dictionary holds the default commands defined by IoSpec.
    """

    COMMANDS_NAMESPACE[cls.__name__.lower()] = cls
    return cls


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

    arg = (arg or '').strip()

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
