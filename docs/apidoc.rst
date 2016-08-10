=================
API documentation
=================

The main entry points to the iospec package are the functions
:func:`iospec.parse` and :func:`iospec.parse_string` functions. Both return a
parse tree structure that consists of an hierarchy of lists and dictionary-like
elements.

**Reference**

.. autofunction:: iospec.parse
.. autofunction:: iospec.parse_string


The IoSpec parse tree
=====================

TestCase elements
-----------------

We refer to each run of a program as a "test case". **iospec** implements many
different test case blocks in order to adapt to different situations. Perhaps
the most simple block is a SimpleTestCase