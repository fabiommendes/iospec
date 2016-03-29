import html
import re
import functools
import inspect


latex_subs = (
    (re.compile(r'\\'), r'\\textbackslash'),
    (re.compile(r'([{}_#%&$])'), r'\\\1'),
    (re.compile(r'~'), r'\~{}'),
    (re.compile(r'\^'), r'\^{}'),
    (re.compile(r'"'), r"''"),
    (re.compile(r'\.\.\.+'), r'\\ldots'),
)


def indent(st, levels=4):
    """Indent string by the given number of spaces or the given indentation
    string"""

    levels = ' ' * levels if isinstance(levels, int) else levels
    lines = [indent + x for x in st.splitlines()]
    return '\n'.join(lines)


def html_escape(x, keep_newlines=False):
    """Escape unsafe HTML characters such as < > & etc"""

    if keep_newlines:
        data = [html_escape(x) for x in x.splitlines()]
        return '\n'.join(data)
    return html.escape(x)


def tex_escape(value):
    """Escape unsafe LaTeX characters.

    LaTeX escaping is unreliable. The grammar can change arbitrarily and some
    othewise safe characters may become unsafe and vice versa. This function
    just offer a decent escape that works in most situations."""

    new = value
    for pattern, replacement in latex_subs:
        new = pattern.sub(replacement, new)
    return new


def static(func):
    """Uses python 3 type hints as static checks"""

    # Process spec info
    spec = inspect.getfullargspec(func)
    arg_hints = {key: hint for (key, hint) in spec.annotations.items()
                           if isinstance(hint, type)}
    ret_hint = arg_hints.pop('return', None)
    arg_T = [arg_hints.get(name) for name in spec.args]
    kwonly = [(name, arg_hints.get(name)) for name in spec.kwonlyargs]
    full_arg_hints = all(x is not None for x in arg_T)

    def raise_type_error_pos(idx, x):
        raise TypeError('argument %r of %s(): must be a %s, got %s' %
                        (spec.args[idx], func.__name__, arg_T[idx].__name__,
                         type(x).__name__))


    #
    # We only implement a few cases based on necessity
    #
    if len(arg_T) == 2 and full_arg_hints:
        @functools.wraps(func)
        def decorated(x, y):
            if not isinstance(x, arg_T[0]):
                raise_type_error_pos(0, x)

            if not isinstance(y, arg_T[1]):
                raise_type_error_pos(1, y)

            return func(x, y)
        return decorated

    raise NotImplementedError