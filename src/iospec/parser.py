import re
from collections import deque

from iospec import *
from iospec.commands import COMMANDS, wrapped_command
from iospec.types import CommentDeque

__all__ = ['parse', 'parse_string', 'IoSpecSyntaxError']


def parse(file, commands=None):
    """Parse the content of file.

    This function accepts file-like objects and a string with a path.
    
    Returns the parsing tree as a dictionary-like structure.
    """
    if isinstance(file, str):
        with open(file) as F:
            data = F.read()
        return parse_string(data)
    return parse_string(file.read(), commands=commands)


def parse_string(text, commands=None):
    """Parse a string of iospec data."""

    parser_job = IoSpecParser(text, commands=commands)
    return parser_job.parse()


class IoSpecSyntaxError(Exception):
    """Raised for errors in iospec syntax."""


class IoSpecParser:
    """
    A parsing job that parses a single IoSpec source.
    """

    def __init__(self, source, commands=None):
        # Prepare global context
        self.source = source
        self.extra_commands = dict(commands or {})
        self.commands = COMMANDS.copy()
        self.commands.update(self.extra_commands)
        self.namespace = {}

        # Initialize parsing job
        self.is_parsed = False
        self.lineno = 0
        self.ast = IoSpec(commands=self.commands)
        self.commands = self.ast.commands
        self.definitions = self.ast.definitions
        self.groups = group_blocks(enumerate(self.source.splitlines(), 1))

    def append_definition(self, definition):
        """
        Append definition to the resulting definitions list.
        """

        self.definitions.append(definition)

    #
    # Parsing functions
    #
    def parse(self):
        """Compute and return the parse tree"""

        if self.is_parsed:
            return self.ast

        # Extract all blocks from source
        for group in self.groups:
            block = self.parse_group(group)
            if block is not None:
                self.ast.append(block)

        self.ast.fuse_outputs()
        self.is_parsed = True
        return self.ast

    def parse_group(self, lines):
        """Parse all lines in group and return the parsed tree."""

        first_line = lines[0][1]

        # Block-start flags
        if first_line.startswith('@command'):
            return self.parse_input_command(lines)
        elif first_line.startswith('@import') or first_line.startswith('@from'):
            return self.parse_import(lines)
        elif first_line.startswith('@plain'):
            return self.parse_plain_input(lines)
        elif first_line.startswith('@input'):
            return self.parse_input_block(lines)
        elif (first_line.startswith('@timeout-error') or
                  first_line.startswith('@build-error') or
                  first_line.startswith('@runtime-error')):
            return self.parse_error_block(lines)
        elif first_line.startswith('@'):
            idx, line = lines[0]
            raise IoSpecSyntaxError(
                'invalid command at line %s: %s' % (idx, line)
            )
        else:
            return self.parse_regular_block(lines)

    def parse_regular_block(self, lines):
        """Make a stream of regular input/output/command strings."""

        stream = []

        while lines:
            idx, line = lines.popleft()
            original_line = line

            # Line-start flags
            if line.startswith('|'):
                line = line[1:]

            out, line = get_output_string(line)
            if Out.is_ellipsis(out):
                stream.append(OutEllipsis(out, fromsource=True))
            else:
                stream.append(Out(out, fromsource=True))

            match = INPUT_TOKEN.match(line)
            if match:
                data = match.group(1)
                stream.append(In(data, fromsource=True))
                continue

            match = COMPUTED_INPUT_TOKEN.match(line)
            if match:
                name, args = match.groups()
                stream.append(self._normalize_computed_input(name, args))
                continue

            if line:
                raise IoSpecSyntaxError(
                    'Invalid output line: %s' % original_line
                )

        return SimpleTestCase(stream, comment=lines.comment)

    def parse_input_command(self, lines):
        idx, line = lines.popleft()
        if line.strip() != '@command':
            raise IoSpecSyntaxError(
                'invalid command in line %s: %s' % (idx, line)
            )

        self.groups.send(lines)
        source = consume_python_code_block(self.groups)

        # Saves in definitions
        self.append_definition('@command\n' + source)

        # Execute source and collect python object
        namespace = {}
        exec(source, self.namespace, namespace)
        if len(namespace) != 1:
            data = ['    ' + line for line in source.splitlines()]
            data = '\n'.join(data)
            raise IoSpecSyntaxError('python source does not define a single'
                                    ' object:\n' + data)
        name, obj = namespace.popitem()
        self.namespace[name] = obj
        self.commands[name] = wrapped_command(obj)

    def parse_import(self, lines):
        idx, line = lines.popleft()
        if lines:
            self.groups.send(lines)

        # Execute imports in global namespace
        exec(line[1:], self.namespace)

        # Block import statements together
        if self.ast.definitions:
            last_def = self.ast.definitions[-1]
            if last_def.startswith('@import') or last_def.startswith('@from'):
                line = '%s\n%s' % (self.ast.definitions.pop(), line)
        self.append_definition(line)

    def parse_plain_input(self, lines):
        lineno, line = lines.popleft()

        # Inline plain input
        if line.strip() != '@plain':
            if not line[6].isspace():
                raise IoSpecSyntaxError(
                    'line %s: expects an whitespace after @plain'
                    % lineno)
            data = line[7:].replace('\\;', '\x00')
            data = [In(x.replace('\x00', ';')) for x in data.split(';')]
            return InputTestCase(
                data,
                inline=True,
                lineno=lineno,
                comment=lines.comment,
            )

        # Block
        self.groups.send(lines)
        data = consume_indented_code_block(self.groups)
        data = strip_columns(data)
        cases = [In(line) for line in data.splitlines()]
        return InputTestCase(
            cases,
            inline=False,
            lineno=lineno,
            comment=lines.comment,
        )

    def parse_input_block(self, lines):
        lineno, line = lines.popleft()

        # Inline plain input
        if line.strip() != '@input':
            inline = True
            if not line[6].isspace():
                raise IoSpecSyntaxError(
                    'line %s: expects an whitespace after @plain' % lineno
                )
            data = line[7:].replace('\\;', '\x00')
            cases = [x.replace('\x00', ';') for x in data.split(';')]

        # Block
        else:
            inline = False
            self.groups.send(lines)
            data = consume_indented_code_block(self.groups)
            data = strip_columns(data)
            cases = data.splitlines()

        for i, x in enumerate(cases):
            x = x.replace('\x00', '\\;')
            if x.startswith('$'):
                match = COMPUTED_INPUT_TOKEN.match(x)
                if match:
                    name, args = match.groups()
                    cases[i] = self._normalize_computed_input(name, args)
                else:
                    raise IoSpecSyntaxError('invalid syntax')
            else:
                cases[i] = In(x)
        return InputTestCase(
            cases,
            inline=inline,
            lineno=lineno,
            comment=lines.comment,
        )

    def parse_error_block(self, lines):
        lineno, line = lines.popleft()
        error_types = ('@timeout-error', '@runtime-error', '@build-error')

        if line.strip() not in error_types:
            raise IoSpecSyntaxError(lineno)
        error_type = line.strip()[1:-6]

        self.groups.send(lines)
        data = consume_indented_code_block(self.groups)
        data = strip_columns(data)
        body_lines = data.splitlines()

        if any(line.startswith('@error') for line in body_lines):
            for i, line in enumerate(lines):
                if line.startswith('@error'):
                    if line.strip() != '@error':
                        raise IoSpecSyntaxError(line)
                    body_lines = lines[:i]
                    error = '\n'.join(lines[i + 1:])
                    break
            else:
                raise RuntimeError
        else:
            error = ''

        body_lines = CommentDeque(enumerate(body_lines, lineno + 1))
        cases = self.parse_regular_block(body_lines)
        return ErrorTestCase(
            list(cases),
            error_type=error_type,
            error_message=error,
            lineno=lineno,
            comment=lines.comment,
        )

    def _normalize_computed_input(self, name, args):
        obj = self.commands[name]
        parsed_args = obj.parse(args)
        return Command(name, args, parsed_args=parsed_args,
                       factory=lambda: obj.generate(parsed_args))


#
# Utility functions
#
def get_output_string(line):
    """
    Scan string from the beginning for an output string syntax.

    Return a (out, tail) tuple where out is the Out() part of the string and
    tail is the beginning of a Command or In block.
    """

    # Line begins with an input block
    if line.startswith('<'):
        return '', line

    # Line may be a command. It depends on the next character being either a
    # letter or a digit.
    if line.startswith('$'):
        if len(line) == 1:
            return '$', ''
        elif line[1].isalnum():
            return '', line

    out, sep, tail = partition_re(line, OUTPUT_TOKEN_SPLIT)
    if sep:
        out += sep[0]
        sep = sep[1:]
        return out, sep + tail
    else:
        return out, ''


def partition_re(string, re):
    """
    Like str.partition(), but uses a regular expression.
    """

    match = re.search(string)
    if match is None:
        return string, '', ''
    else:
        i, j = match.start(), match.end()
        return string[0:i], string[i:j], string[j:]


def group_blocks(line_iter):
    """Groups lines of each session block together.

    The input is a list of (line_index, line) pairs. Return an iterator over a
    list of lines in each group."""

    session = CommentDeque()
    lines = deque(line_iter)
    lines.append((None, ''))
    comments = []

    while lines:
        idx, line = lines.popleft()

        # Whitespace and comments divide chunks
        if (not line) or line.isspace() or line.startswith('#'):
            comments.append((idx, line))

            if not session:
                continue

            if comments:
                data = '\n'.join(line for (_, line) in comments)
                data = data.strip()
                if data:
                    comment_idx = comments[0][0]
                    session.comment = Comment(data, lineno=comment_idx)
                comments = []
            data = yield session
            while data is not None:
                yield data
                data = yield session

            session = CommentDeque()
        else:
            session.append((idx, line))


def consume_python_code_block(groups):
    """Return a node that collects the source code for a python class or
    function definition. Return a string of source code"""

    lines = next(groups)
    lineno, line = lines.popleft()
    head = line

    # Consume all decorators
    while line.startswith('@'):
        lineno, line = lines.popleft()
        head += '\n' + line

    if not line.startswith('def') or line.startswith('class'):
        raise IoSpecSyntaxError(
            'expect function or class definition on line: %s' % lineno
        )

    # Add all lines to source
    groups.send(lines)
    data = consume_indented_code_block(groups)
    return '%s\n%s' % (head, data)


def consume_indented_code_block(groups):
    """Consume all indented lines in groups and return the source string."""

    source = []
    lines = CommentDeque()

    for lines in groups:
        go = True
        while lines:
            idx, line = lines.popleft()
            if line and line[0].isspace():
                source.append(line)
            else:
                lines.appendleft((idx, line))
                go = False
                break
        if not go:
            break
    if lines:
        groups.send(lines)

    return '\n'.join(source)


def strip_columns(data, n=4):
    """
    Strip n of the leftmost columns.

    Raises an error if any non-whitespace content is found in these columns.
    """

    def error(st):
        raise IoSpecSyntaxError(
            'line must be empty up to the %s-th column, got %r' % (n, st)
        )

    lines = data.splitlines()

    for idx, line in enumerate(lines):
        if len(line) >= n:
            lines[idx] = line[4:]
            if set(line[:4]) != {' '}:
                error(line)
        elif not line or set(line) == {' '}:
            lines[idx] = ''
        else:
            error(line)

    return '\n'.join(lines)


#
# Regex and token definitions
#
OUTPUT_TOKEN = re.compile(r'''
^(
    (?:    
        (?:\\.)*   # Match any escaped characters
        [^<\$]*    # Match any non-$/< sequence
    )*             # Perform zero or more of these matches
)(.*)$
''', flags=re.VERBOSE)

OUTPUT_TOKEN_SPLIT = re.compile(r'[^\\]<|[^\\]\$[a-zA-Z0-9_]')

INPUT_TOKEN = re.compile(r'^<(.*)>\s*$')

COMPUTED_INPUT_TOKEN = re.compile(r'^\$([a-zA-Z]+)(?:[(](.*)[)])?\s*$')

ENUMERATED_INPUT_TOKEN = re.compile(r'^\$([0]+)\s*$')

INPUT_VALUE_TOKEN = re.compile(r'''
^(
    (?:
        [^;]*
        (?:\\.)*
    )*
);''', flags=re.VERBOSE)
