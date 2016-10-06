import html
import re


latex_subs = (
    (re.compile(r'\\'), r'\\textbackslash'),
    (re.compile(r'([{}_#%&$])'), r'\\\1'),
    (re.compile(r'~'), r'\~{}'),
    (re.compile(r'\^'), r'\^{}'),
    (re.compile(r'"'), r"''"),
    (re.compile(r'\.\.\.+'), r'\\ldots'),
)


def indent(st, levels=4):
    """
    Indent string by the given number of spaces or the given indentation
    string.
    """

    indent_st = ' ' * levels if isinstance(levels, int) else levels
    lines = [indent_st + x for x in st.splitlines()]
    return '\n'.join(lines)


def html_escape(x, keep_newlines=False):
    """
    Escape unsafe HTML characters such as < > & etc.
    """

    if keep_newlines:
        data = [html_escape(x) for x in x.splitlines()]
        return '\n'.join(data)
    return html.escape(x)


def tex_escape(value):
    """
    Escape unsafe LaTeX characters.

    LaTeX escaping is unreliable. The grammar can change arbitrarily and some
    otherwise safe characters may become unsafe and vice versa. This function
    just offer a decent escape that works in most situations.
    """

    new = value
    for pattern, replacement in latex_subs:
        new = pattern.sub(replacement, new)
    return new


def partition_re(string, re):
    """
    Like str.partition(), but uses a regular expression to split contents.
    """

    match = re.search(string)
    if match is None:
        return string, '', ''
    else:
        i, j = match.start(), match.end()
        return string[0:i], string[i:j], string[j:]
