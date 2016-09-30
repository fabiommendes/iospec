===============
IoSpec's syntax
===============

This section describes the IoSpec's syntax in greater detail.


Simple I/O blocks
=================

If you need to specify a fixed sequence of inputs/outputs from a program just
use the following syntax::

    # A line of comment
    Name: <Mary>
    Hello Mary!

    Name: <John>
    Hello John!

IoSpec interprets anything inside angle brackets as input strings and the rest
as output (and interpret it mostly verbatim). Different test cases are separated
by blank lines.


A pipe character (``|``) in the begging of a line is ignored. This is useful to
define output blocks that may contain blank lines:

.. code-block:: text

    Say your name: <Mary>
    |Hello, Mary.
    |
    |Nice to meet you.

If the the line starts with two pipes (``||``), the first will be ignored and
the second one will be included in the output block. It can can also be used to
escape comments:

.. code-block:: text

    # This is a comment and is ignored.
    # A comment line *must* start with #. There is no inline comment.
    |# A line of of output that starts with a hash
    || A line of output that starts with a single pipe


Another special behavior is triggered by the ellipsis sequence. The example
above could be written as:

.. code-block:: text

    Say your name: <Mary>
    Hello, Mary...Nice to meet you.

In this case, the ellipsis will match any sequence of characters (including
newlines). The two examples are not exactly the same since the second one
will match any output that starts with the substring "Hello, Mary" and ends
with "Nice to meet you.". The first example expects a single newline between
both.

The ellipsis can be escaped using the "\..." sequence:

.. code-block:: text

    Quote: <John>
    War is over\... If you want it.


Escape sequences
----------------

What if the output of my program contain a ``"<"`` character? Some special
sequences must be escaped as ``\<`` on output streams.

+----------+----------+----------+------------------------------------------------+
| Sequence | Stream   | Escape   | Description                                    |
+==========+==========+==========+================================================+
| ``...``  | output   | ``\...`` | Captures arbitrary output values               |
+----------+----------+----------+------------------------------------------------+
| ``<``    | output   | ``\<``   | Begin an <input> block                         |
+----------+----------+----------+------------------------------------------------+
| ``$``    | anywhere | ``\$``   | Declare a computed input                       |
+----------+----------+----------+------------------------------------------------+


Input blocks
============

A common requirement of an online judges is to have a way to compute the sequence
of inputs and outputs from a reference implementation. IoSpec can specify
input-only runs, which can be used by third parties to compute the corresponding
outputs from some specific program.

If you are interested in doing this, consider the `edjuge <http://github.com/fabiommendes/ejudge>`
package. It integrates with iospec to make just that. Remember that iospec only
cares about *representing* how a program should run in terms of the expected
inputs and outputs. It is not concerned about actually running these programs.

There are a few basic commands that define input-only blocks. The ``@input``
command defines a block in which each input is either separated by semicolons
or by newlines:

.. code-block:: text

    # Here we specify only the inputs of a program
    # Be careful to avoid putting spurious spaces between your inputs
    @input John;Paul;George;Ringo;$name

    # Indentation is very important and must be **exactly** 4 spaces long.
    @input
        Mel C
        Mel B
        Posh
        Baby
        Ginger

The inline version of this command uses ``\;`` to escape semicolons in the
input strings. Notice that the semi-colon should not be escaped outside
the inline input block.

A single trailing semi-colon in the inline version of this command is ignored.
If you want to specify that the last input is empty, it is necessary to put
two trailing semi-colons::

    @input the;last;input;is;empty;;


Input commands
==============

Until now we saw only simple fixed inputs that uses the ``<syntax>``. IoSpec can
compute input values automatically from a random value generator. For this to
work, we have to replace the angle brackets with a dollar sign identifier::

    Say your name: $name
    Hello, ...!

The $name input string will be picked randomly by the iospec runner, yielding
plausible names.

There are many accepted identifiers and some of them can also receive
arguments. The arguments (when they exist) should be separated by commas
and enclosed in parenthesis. The most common identifiers are shown in the table
bellow:

+----------------+-------------------------------------------------------------+
| Identifier     | Description                                                 |
+================+=============================================================+
| $name          | A random single-word ASCII name with no spaces. Accepts an  |
|                | optional numerical argument specifying the maximum string   |
|                | size. (default is 20).                                      |
+----------------+-------------------------------------------------------------+
| $fullname      | Like $name, but may contain spaces                          |
+----------------+-------------------------------------------------------------+
| $ascii(N)      | A random ascii string with N characters                     |
+----------------+-------------------------------------------------------------+
| $str(N)        | A random utf8 string with N characters                      |
+----------------+-------------------------------------------------------------+
| $text(N)       | A random ascii string with N characters that may contain    |
|                | newlines.                                                   |
+----------------+-------------------------------------------------------------+
| $int           | An integer. The default numerical range is (0, 1000). You   |
|                | may define different ranges by calling either $int(x), for  |
|                | the [0, x] interval or $int(a, b) for the [a, b] interval.  |
+----------------+-------------------------------------------------------------+
| $float         | Similar to $int, but generates floating point numbers       |
+----------------+-------------------------------------------------------------+

Similarly to regular inputs, a computed input string should always finish its
line. This emulates the user hitting <return> in an interaction with a computer
program. Any non-whitespace character after either a regular input or after a
computed input is considered illegal. This behavior simplifies the parser
and also simplifies the creation of input files: the closing > and the dollar
sign do not need to be escaped inside input strings. The strings ``\$`` and
``\<`` are always treated as escape sequences regardless if they are present
inside input or output strings:

.. code-block:: text

    Always escape these characters in the output: \$, \<, \n and \\
    The following lines are the same:
        Currency: <U$>
        Currency: <U\$>

User definded commands
======================

Sometimes you may find that the default input commands are too limited. New
commands can be created in IoSpec source by defining a Python function with
a ``@command`` decorator:

.. code-block:: text

    @import random

    @command
    def beatle(st):
        return random.choice(['John', 'Paul', 'George', 'Ringo'])

    Name: $beatle
    You rock!

The input function receives a single string argument (which corresponds to
the string content inside parenthesis). The return value is converted to a
string and used as an input argument.

The ``@from`` and ``@import`` commands are useful to import names to the script
namespace when defining these functions. These two commands closely correspond
to their Python counterparts, but do not accept multi-line imports. Users can
also define modules with third part commands that can be imported using a
``@import my_commands`` statement. If the module has a public
``iospec_commands`` attribute, it will be treated as a dictionary that maps
command names to their respective implementations.

We can also decorate a Python class with a ``@command`` decorator. In this case,
the class must implement the two methods described bellow.

.. code-block:: text

    @command
    class beatles:
        beatles = ['John', 'Paul', 'George', 'Ringo']

        def parse(self, args):
            """Parse the argument string. The output of this function is passed
            to the generate() method.

            It should raise an SyntaxError if the arguments are not valid. This
            error reaches the user during parsing of the iospec file."""

            value = int(args)
            if not (0 <= value <= 3):
                raise SyntaxError
            return value

        def generate(self, argument):
            """This function is called to generate a new value from the
            arguments passed through the parse() method."""

            return self.beatles[argument]

The class solution is more robust and probably should be preferred in command
libraries. The greatest advantage is that arguments are parsed (and thus
errors are found) during the parsing phase. Functions are only executed during
command execution.


.. advanced inputs
    Advanced computed inputs
    ------------------------

    Sometimes even personalized input commands are not flexible enough. One may need
    to generate successive inputs that have some special relation with each other.
    For instance, the vertices of a convex polygon cannot be created by a naive
    ``$point`` command: a set of random vertices is very likely to form convex and
    concave polygons alike.

    The solution is to use the ``@generator`` decorator to mark a python
    generator function that computes inputs in batch. These inputs can be referred
    by the identifiers $0, $1, $2, etc in a block that starts with the @generate
    command:

    .. code-block:: text

        @import random

        @generator
        def increasing_numbers(N):
            N = int(N)
            yield from sorted([random.random() for _ in range(N)])

        @generate increasing_numbers(2)
            Smaller: $0
            Larger: $1
            Sum: ...


Error blocks
============

Sometimes we need to specify that a program was terminated with some error condition.
IoSpec defines tree types of error: build errors, timeout errors, and runtime
errors.

Build errors
------------

A build error describe situations when the program could not even run and
is typically used to describe compile-time or syntax errors. A build error block
is declared with the syntax::

    @build-error
        File "main.py", line 42
        x = a b
              ^

        SyntaxError: invalid syntax

The build-error block consists of the @build-block decorator followed by a
4-spaces indented block that contains the text of the error message. IoSpec
syntax is ignored inside this block and error messages can be simply copied and
pasted to these blocks.


Timeout errors
--------------

Timeout errors are reserved for runs that had not finished, but were terminated
due to time constraints. Program could be correct (albeit a little slow) or
could be stuck on an infinite loop. One never knows.

A timeout error declaration simply wraps a standard IO block::

    @timeout-error
        Name: <Maria>
        Hello Maria!

The IO block should show the sequence of inputs and outputs shown before the
program has been terminated.


Runtime errors
--------------

Finally, the last condition is reserved for runtime errors such as segfaults,
exceptions, etc. It has the most complicated declaration since it wraps both
the part that describes a valid program execution and the captured stderr that
was printed due to a faulty program execution:

    @runtime-error
        x: <0>

    @error
        Traceback (most recent call last)
            "main.py" in main()
                --> print('answer:', 42 / x)

        ZeroDivisionError: division by zero

The @error works like a @build-error and simply declares the error message. It
should follow a @runtime-error declaration, otherwise is considered to be invalid.

If you want to describe a program that raises an error before any IO, it is
possible to join both blocks::

    @runtime-error
    @error
        Traceback (most recent call last)
            "main.py" in main()
                --> import Math

        ImportError: No module named 'Math'
