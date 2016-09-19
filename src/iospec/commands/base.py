class Command:
    """
    Base class for Command objects.
    """

    @classmethod
    def from_arguments(cls, argstring):
        """
        Initializes command object from unparsed args string.
        """

        obj = object.__new__(cls)
        obj.parse(argstring)
        return obj

    def parse(self, data):
        """
        Parse content of command string.
        """

    def generate(self):
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


class FakerString(Command):
    """
    Base class for all commands that take a random string from faker-factory
    and return a value with some possibly maximum length.
    """

    def __init__(self, maxsize=None):
        self.maxsize = maxsize

    def parse(self, size):
        if size is None:
            self.maxsize = None
        else:
            self.maxsize = int(size)

    def generate(self):
        if self.maxsize is None:
            return self.fake()

        # Try to generate a valid value a few times. If we fail, we generate
        # some random name and truncate.
        value = None
        for _ in range(25):
            value = self.fake()
            if len(value) <= self.maxsize:
                return value
        return value[:self.maxsize]

    def fake(self):
        raise NotImplementedError('must be overridden in subclasses')


class NumericBase(Command):
    """
    Numeric ranges in a given interval.
    """

    min_value = -1000000
    max_value = 1000000

    def __init__(self, start=None, stop=None):
        if start is None and stop is None:
            self.start = self.min_value
            self.stop = self.max_value
        elif start is not None and stop is None:
            self.start = -start
            self.stop = start
        else:
            self.start = start
            self.stop = stop


