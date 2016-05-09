import os
from setuptools import setup, find_packages

NAME = 'iospec'
DIRNAME = os.path.dirname(__file__)

# Rewrite __version__.py
VERSION = open('VERSION').read().strip()
version_file = os.path.join(DIRNAME, 'src', NAME, '__version__.py')
with open(version_file, 'w') as F:
    F.write('__version__ = %r\n' % VERSION)


# Configure setup
distribution = setup(
    name=NAME,
    version=VERSION,
    description=
    'Lightweight markup for the description of running sessions of '
    'input/output based programs in the context of an online judge',
    author='Fábio Macêdo Mendes',
    author_email='fabiomacedomendes@gmail.com',
    url='https://github.com/fabiommendes/iospec',
    long_description=open('README.rst').read(),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries',
    ],

    # Packages and depencies
    package_dir={'': 'src'},
    packages=find_packages('src'),
    install_requires=['jinja2', 'pygeneric>=0.3', 'faker-factory'],
    package_data={
        '': ['templates/*.*'],
    },

    # Scripts
    entry_points={
        'console_scripts': ['iospec = iospec.__main__:main'],
    },
    zip_safe=False,
)
