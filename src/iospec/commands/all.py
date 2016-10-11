import random as _random

from iospec.commands import base
from iospec.commands.utils import iscommand, parse_number as _parse_number


class FakeProxy:
    def __init__(self):
        self.__fake = None

    def __getattr__(self, attr):
        if self.__fake is None:
            from faker import Factory
            self.__fake = Factory.create()

        return getattr(self.__fake, attr)

_fake = FakeProxy()


@iscommand
class Name(base.FakerString):
    """
    A random name.

        $name     --> random string with a plausible name.
        $name(xx) --> name is truncated to have at most xx characters.

    Names generated with this function usually have spaces.
    """

    def fake(self):
        return _fake.name()


@iscommand
class FirstName(base.FakerString):
    """
    A random name.

        $firstname     --> random string with a plausible name.
        $firstname(xx) --> name is truncated to have at most xx characters.

    Names generated with this function do not have any spaces.
    """

    def fake(self):
        name = ' '
        while ' ' not in name:
            name = _fake.first_name()
        return name


@iscommand
class LastName(base.FakerString):
    """
    A random name.

        $lastname     --> random string with a plausible name.
        $lastname(xx) --> name is truncated to have at most xx characters.

    Names generated with this function do not have any spaces.
    """

    def fake(self):
        name = ' '
        while ' ' not in name:
            name = _fake.last_name()
        return name


@iscommand
class Email(base.FakerString):
    """
    A random e-mail.

        $e-mail     --> random string with a plausible e-mail.
        $e-mail(xx) --> e-mail is truncated to have at most xx characters.

    Names generated with this function do not have any spaces.
    """

    def fake(self):
        name = ' '
        while ' ' not in name:
            name = _fake.email()
        return name


@iscommand
class Str(base.FakerString):
    """
    A random string.

        $str     --> random string of text.
        $str(xx) --> string is truncated to have at most xx characters.

    Strings generated with this function do not have any new lines.
    """

    def fake(self):
        data = '\n'
        while '\n' not in data:
            data = _fake.pystr()
        return data


@iscommand
class Text(base.FakerString):
    """
    A random string.

        $text     --> random string of text.
        $text(xx) --> string is truncated to have at most xx characters.

    Strings generated with this function have new lines separating paragraphs.
    """

    def fake(self):
        return '\n\n'.join(_fake.paragraphs())


@iscommand
class Paragraph(base.FakerString):
    """
    A random string.

        $paragraph     --> random paragraph with multiple sentences.
        $paragraph(xx) --> string is truncated to have at most xx characters.

    Strings generated with this function do not have new lines.
    """

    def fake(self):
        return _fake.paragraph()


@iscommand
class Fake(base.Command):
    """
    Return a random fake data.

    Any method from Python's fake-factory package is accepted.

    Example:

        $fake(email) --> return a random e-mail.
    """

    def __init__(self, faker):
        self.faker = faker

    def parse(self, attr):
        blacklist = [
            'add_provider', 'format', 'get_formatter', 'get_providers' 'parse',
            'provider', 'providers', 'set_formatter',
        ]
        if attr.startswith('_') or attr not in dir(_fake) or attr in blacklist:
            raise SyntaxError('invalid fake method: %s' % attr)
        self.faker = attr

    def generate(self):
        return getattr(_fake, self.faker)()


@iscommand
class Int(base.NumericBase):
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
        self.__init__(*_parse_number(arg, int))

    def generate(self):
        return _random.randint(self.start, self.stop)


@iscommand
class Float(base.NumericBase):
    """
    Any random floating point number.

    Accept the same arguments as integers.
    """

    def parse(self, arg):
        self.__init__(*_parse_number(arg, float,
                                     minvalue=-2 ** 50, maxvalue=2 ** 50))

    def generate(self):
        return _random.uniform(self.start, self.stop)


@iscommand
class Digit(base.NoArgCommand):
    """
    A one digit number.
    """

    def generate(self):
        return _random.randint(0, 9)


@iscommand
class SmallFloat(base.NoArgCommand):
    """
    A small floating point number between zero and one.
    """

    def generate(self):
        return _random.uniform(0, 1)


class Foo(base.Command):
    """
    A simple echoing command useful for testing. This name is not exported
    to the default commands dictionary but can be inserted on any parse tree
    by setting

    >>> parse_tree(source, commands={'foo': Foo()})             # doctest: +SKIP

    The Foo command expands to the string "foo" or a repetition such as
    $foo(2) --> "foofoo"
    """

    def __init__(self, repetitions=1):
        self.repetitions = repetitions

    def parse(self, args):
        self.repetitions = int(args or '1')

    def generate(self):
        return 'foo' * self.repetitions


# Clean namespace
del base, iscommand, FakeProxy

