lispython
=========

Custom source file encoding for Python - converts Lisp-like syntax to Python.

Requirements:

    * pip install pyparsing

How to run::

    python runthis.py

This is not a Lisp! No cars, no cdrs, no cons pairs, no let's, no macros, no nothing. Only parentheses. Translation to Python is pretty straightforward.

TODO
----

 - fix priority loss in expressions (around line 210 in lpencoder.py)
 - add support for Python docstrings, comments and more cleaner code generation

