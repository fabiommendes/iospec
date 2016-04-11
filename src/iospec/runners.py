import io
import sys
import functools
from collections import deque
from iospec.types import In, Out


__all__ = ['IoObserver']


class IoObserver:
    """
    Implements functions that helps to track the flow of inputs and outputs in
    a Python session.

    It implements an ``input`` and a ``print`` methods that works as drop-in
    replacements for the corresponding Python's functions.

    Example
    -------

    We create a new observer and export its print and input methods to a
    dictionary namespace.

    >>> io_obs = IoObserver(['foo'])
    >>> namespace = {
    ...     'print': io_obs.print,
    ...     'input': io_obs.input,
    ... }
    >>> exec('''
    ... name = input('What is your name? ')
    ... print('Hello %s' % name)
    ... ''', namespace)

    All interactions with print and Xinput were recorded. We can obtain a list
    of interaction using the flush() method. This cleans the recording data
    and returns what was already registered by the observer.

    >>> io_obs.flush()
    [Out('What is your name? '), In('foo'), Out('Hello foo')]
    >>> io_obs.interactions()
    []
    """

    __print = staticmethod(print)
    __input = staticmethod(input)

    class EmptyInputError(RuntimeError):
        pass

    def __init__(self, inputs=()):
        self._stream = []
        self._inputs = deque()
        if isinstance(inputs, str):
            self.append_input(inputs)
        else:
            for value in inputs:
                self.append_input(value)

    def flush(self, stripend=True):
        """Flush all stored input/output interactions and return a list with
        all registered activities."""

        result = self._stream
        self._inputs = deque()
        self._stream = []

        # Strip newline from last output interaction
        if (stripend and result and isinstance(result[-1], Out)
                     and result[-1].data.endswith('\n')):
            result[-1].data = result[-1].data[:-1]
        return result

    def interactions(self):
        """Return a list of interactions that happened so far."""

        return list(self._stream)

    @functools.wraps(print)
    def print(self, *args, sep=' ', end='\n', file=None, flush=False):
        if not (file is None or file is sys.stdout):
            self.__print(*args, sep=sep, end=end, file=file, flush=flush)
        else:
            file = io.StringIO()
            self.__print(*args, sep=sep, end=end, file=file, flush=flush)
            self.write_output(file.getvalue())

    @functools.wraps(input)
    def input(self, prompt=None):
        if prompt is not None:
            self.write_output(prompt)
        return self.next_input()

    def write_output(self, data):
        """This function should be called instead of (or in addition to) writing
        data to the standard output."""

        if self._stream and isinstance(self._stream[-1], Out):
            self._stream[-1].data += data
        else:
            self._stream.append(Out(data))

    def write_input(self, data):
        """This function should be called instead of (or in addition to) writing
        a line of text to the standard output.

        The input data should end in a newline."""

        if not data.endswith('\n'):
            msg = 'received an incomplete line of input: %r' % data
            raise RuntimeError(msg)

        self._stream.append(In(data[:-1]))

    def next_input(self):
        """Consume the next input on the list of inputs"""

        try:
            value = self._inputs.popleft()
        except ValueError:
            raise self.EmptyInputError('input list is empty')
        self.write_input(value + '\n')
        return value

    def append_input(self, inpt):
        """Add a new input value to the end of list.

        If the string has a newline, it will be split into different input
        values, one per line.
        """

        if not isinstance(inpt, str):
            raise TypeError('expect strings, got %r' % inpt)
        lines = inpt.splitlines(keepends=False)
        self._inputs.extend(lines)

    def extend_inputs(self, seq):
        """Append sequence of inputs to the end of the input list"""

        for inpt in seq:
            self.append_input(inpt)

    def prepend_input(self, inpt):
        """Like append_input, but add inputs to the beginning of the queue."""

        for line in reversed(inpt.splitlines(keepends=False)):
            self._inputs.appendleft(line)

    def clear_inputs(self):
        """Clear the list of pending inputs."""

        self._inputs = deque()

    def inputs(self):
        """Return a list of pending inputs."""

        return list(self._inputs)
