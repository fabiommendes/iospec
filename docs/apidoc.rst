=================
API documentation
=================

The main entry points to the iospec package is the function
:func:`iospec.parse`. it returns a :class:`iospec.IoSpec` parse tree.

**Reference**

.. autofunction:: iospec.parse


The IoSpec parse tree
=====================

The result of :func:`iospec.parse` is a :class:`iospec.IoSpec` instance that
behaves mostly like a sequence of test case nodes. Consider the string
of iospec data:

.. code-block:: python

    data = """
    Say your name: <John>
    Hello, John!
    """

The contents can be parsed as:

.. code-block:: python

    from iospec import parse
    tree = parse(data)
    case = tree[0]

Each test case is a sequence of In/Out strings:

>>> list(case)
[Out('Say your name: '), In('John'), Out('Hello, John!')]

The main AST object
-------------------

.. autoclass:: iospec.datatypes.IoSpec

TestCase elements
-----------------

We refer to each run of a program as a "test case". **iospec** implements many
different test case blocks in order to adapt to different situations. Perhaps
the most simple block is a SimpleTestCase

.. autoclass:: iospec.datatypes.SimpleTestCase

.. autoclass:: iospec.datatypes.InputTestCase

.. autoclass:: iospec.datatypes.ErrorTestCase

.. autoclass:: iospec.datatypes.TestCase


Introspecting the tree
----------------------

IoSpec instances and all their child nodes define a few convenience attributes
that helps assess the tree state. All elements in the IoSpec tree define the
following attributes

is_input/has_input:
    True if all/any leaves represent inputs.
is_output/has_output:
    True if all/any leaves represent outputs.
is_expanded/has_expanded:
    A expanded node requires no command evaluation and can be used directly
    in order to compare the real input/output from a program. A example of a
    non-expanded node is a command such as $int(1, 10).
is_safe/has_safe:
    A safe node does not require any external code evaluation. Custom commands
    are not safe, but builtin commands are. @input blocks are not safe because
    they require an external program to generate the complete IO interaction.
is_simple/has_simple:
    Simple nodes can be used directly to compare the IO from a program. Simple
    nodes uses only simple In/Out strings.
