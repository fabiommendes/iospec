.. image:: https://travis-ci.org/fabiommendes/iospec.svg?branch=master
    :target: https://travis-ci.org/fabiommendes/iospec

.. image:: https://coveralls.io/repos/github/fabiommendes/iospec/badge.svg?branch=master
    :target: https://coveralls.io/github/fabiommendes/iospec?branch=master

The IoSpec format is a lightweight markup for specifying the expected inputs and
outputs for running a program in an online judge setting. It is designed to be
unobtrusive in the simple cases, while still having some some advanced
features. This package defines the IoSpec format and provides a Python parser
for it.


Basic syntax
============

A basic session of an input/output based program running on an
online judge is specified like this:

.. code-block:: text

    Say your name: <John>
    Hello, John!
    
In this example, the string between angle brackets is considered to be an input
and everything else is the expected output. Different runs should be separated by 
blank lines:

.. code-block:: text

    Say your name: <John>
    Hello, John!
    
    Say your name: <Mary>
    Hello, Mary!

We call each of these runs an iospec "test case". The above example is declaring an
interaction in which given the input ``John``, the program should print ``Hello, John!``
while in the second run, when the input will be ``Mary``, and the program will print
``Hello, Mary!``.

A IoSpec source file consists of any number of test cases and some special
blocks and directives that will be discussed afterwards.

This example is just the surface: IoSpec syntax has commands to define automatic
inputs, capture patterns, execution errors and more! Check the manual if you
want to learn more.