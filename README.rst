The IoSpec format is a lightweight markup for specifying the expected inputs and
outputs for running a program in an online judge setting. It is designed to be
unobtrusive in the simple cases, while still having some some advanced
features. This package defines the IoSpec format and provides a Python parser
to it.


Basic syntax
============

A basic session of an input/output based program running on an
online judge is specified like this::

    Say your name: <John>
    Hello, John!
    
In this example, the string between angle brackets is considered to be an input
and everything else is the expected output. Different runs should be separated by 
a blank line::

    Say your name: <John>
    Hello, John!
    
    Say your name: <Mary>
    Hello, Mary!

We call each of these runs an iospec "test case". What we are saying in the above
example is that when given the input ``John``, the program should print ``Hello, John!`` while
in the second run, when the input will be ``Mary``,  the program should print 
``Hello, Mary!``.

A IoSpec source file consists of any number of test cases and some special
blocks and directives that will be discussed afterwards.


Output blocks and comments
--------------------------

If the output string spans multiple lines that could include one or more blank lines,
one should start each line with pipe character::

    Say your name: <Mary>
    |Hello, Mary.
    |
    |Nice to meet you.

The pipe character only has effect if it starts a line. The pipe is not rigorously
necessary in the second and fourth lines, but probably should be there for
clarity. If the the line starts with two pipes, the first will be ignored and
the second one will be included in the expected output. This method can be used to escape
comments, as well::


    # This is a comment and is ignored.
    # Comments can only appear between runs and there is no concept of a inline
    # comment.
    |# This specify a line of output that starts with a hash
    || This specify a line of output that starts with a single pipe


Another special behavior is triggered by the ellipsis sequence. The example
above could be written as::

    Say your name: <Mary>
    Hello, Mary...Nice to meet you.

In this case, the ellipsis will match any sequence of characters (including
newlines). The two examples are not exactly the same since the second one
will match any output that starts with the substring "Hello, Mary" and ends
with "Nice to meet you.". The first example expects a single newline between
both.

The ellipsis can be escaped using the "\..." sequence::

    Quote: <John>
    War is over\... If you want it.


The parse tree
--------------

IoSpec sources are parsed using either the :func:`iospec.parse(F)` or
:func:`iospec.parse_string(src)` functions. Both return a :cls:`iospec.IoSpec`
instance that behaves like a sequence of test case nodes. Consider the file::

    Say your name: <John>
    Hello, John!

The contents can be parsed as::

    >>> from iospec import parse
    >>> tree = parse(data_file)
    >>> case = tree[0]

Each test case is a sequence of In/Out strings::

    >>> list(case)
    [Out('Say your name: '), In('John'), Out('Hello, John!')]


Input commands
==============

Inputs can be computed automatically by a random value generator. For this, we
replace the angle bracket syntax with a dollar sign identifier::

    Say your name: $name
    Hello, ...!

The $name input string will be picked randomly by the iospec runner. We 
introduced the ellipsis syntax: it is used to match any number of characters
inside the line (followed by an exclamation mark, in this case).

There are many accepted indentifiers and some of them can also receive 
arguments. The arguments (when they exist) should be separated by commas
and enclosed in parenthesis. We list all supported indentifiers in the table 
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
| $int           | An integer. The default numerical range is that of a 32-bit |
|                | number. $int(+) chooses only positive integers (use $int(-) |
|                | for negative ones. We can set a range using the $int(a:b)   |
|                | syntax. Optionally $int(+a), $int(-a) can be used for       |
|                | positive and negative ranges containing zero and $int(a)    |
|                | defines a symmetric range.                                  |
+----------------+-------------------------------------------------------------+
| $float         | Similar to $int, but generates floating point numbers       |
+----------------+-------------------------------------------------------------+

Similarly to regular inputs, a computed input string should always finish its
line. This emulates the user hitting <return> in an interaction with a computer
program. Any non-whitespace character after either a regular input or after a
computed input are considered illegal. This behavior simplifies the parser
and also simplifies the creation of input files: the closing > and the dollar 
sign do not need to be escaped inside input strings. The strings ``\$`` and
``\<`` are always treated as escape sequences regardless if they are present
inside input or output strings::

    Always escape these characters in the output: \$, \<, \n and \\
    The following lines are the same:
        Currency: <U$>
        Currency: <U\$>

Defining commands
-----------------

Sometimes you may find that the default input commands are too limited. New
commands can be created in the IoSpec source by defining a Python function with
a ``@command`` decorator::

    @import random
    
    @command
    def beatle(st):
        return random.choice(['John', 'Paul', 'George', 'Ringo'])
        
    Name: $beatle
    You rock!
    
The input function must receive a single string argument (which corresponds to
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

::

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
            
        def generate(self, value):
            """This function is called to generate a new value from the 
            arguments passed through the parse() method."""
            
            return self.beatles[value]

The class solution is more robust and probably should be preferred in command
libraries. The greatest advantage is that arguments are parsed (and thus
error are catch) during the parsing phase. Functions are only executed during
command execution.


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
command::

    @import random
    
    @generator
    def increasing_numbers(N):
        N = int(N)
        yield from sorted([random.random() for _ in range(N)])
        
    @generate increasing_numbers(2)
        Smaller: $0
        Larger: $1
        Sum: ...

        
Input blocks
============

The IoSpec also can specify input-only runs, which are useful in the case a
third party computes the corresponding outputs from a reference program.
There are a few basic commands that define input-only blocks. The ``@input``
command defines a block in which either each input is separated by semicolons
or each input corresponds to a line in an indented block bellow the command::

    # Here we specify only the inputs of a program
    @input John;Paul;George;Ringo;$name

    # Indentation is very important and must be exactly 4 spaces long.
    @input
        Mel C
        Mel B
        Posh
        Baby
        Ginger

The inline version of this command uses ``\;`` to escape semicolons in the
input strings. Both versions accept computed inputs and a ``@generate`` decorator
preceding the block.

