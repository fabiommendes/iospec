# -*- coding: utf-8 -*-
#
# This file were created by Python Boilerplate. Use boilerplate to start simple
# usable and best-practices compliant Python projects.
#
# Learn more about it at: http://github.com/fabiommendes/python-boilerplate/
#

import os
from setuptools import setup, find_packages

# Save version and author to __meta__.py
version = open('VERSION').read().strip()
dirname = os.path.dirname(__file__)
path = os.path.join(dirname, 'src', 'iospec', '__meta__.py')
meta = '''# Automatically created. Please do not edit.
__version__ = u'%s'
__author__ = u'F\\xe1bio Mac\\xeado Mendes'
''' % version
with open(path, 'w') as F:
    F.write(meta)

setup(
    # Basic info
    name='iospec',
    version=version,
    author='Fábio Macêdo Mendes',
    author_email='fabiomacedomendes@gmail.com',
    url='',
    description=
        'Lightweight markup for the description of running sessions of '
        'input/output based programs in the context of an online judge',
    long_description=open('README.rst').read(),

    # Classifiers (see https://pypi.python.org/pypi?%3Aaction=list_classifiers)
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Topic :: Software Development :: Libraries',
    ],

    # Packages and dependencies
    package_dir={'': 'src'},
    packages=find_packages('src'),
    install_requires=[
        'jinja2>=2.7',
        'pygeneric>=0.3',
        'unidecode',
        'fake-factory'
    ],
    extras_require={
        'dev': [
            'python-boilerplate',
            'invoke>=0.13',
            'pytest',
            'pytest_cov',
            'manuel',
        ],
    },

    # Scripts
    entry_points={
        'console_scripts': ['iospec = iospec.__main__:main'],
    },

    # Package data
    package_data={
        '': ['templates/*.*'],
    },

    # Other configurations
    zip_safe=False,
    platforms='any',
)