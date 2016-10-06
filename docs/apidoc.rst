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