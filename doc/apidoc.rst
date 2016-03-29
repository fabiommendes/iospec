=================
API documentation
=================

The IOSpec parse tree
=====================

The main entry points to the iospec package are the functions
:func:`iospec.parse` and :func:`iospec.parse_string` functions. Both return a
parse tree structure that consists of an hierarchy of lists and dictionary-like
elements.

TestCase elements
-----------------

We refer to each run of a program as a "test case". The IOSpec implements many
different test case blocks in order to adapt to different situations. Perhaps
the most simple block is a PlainInput