from iospec.exceptions import BuildError


def executor(src):
    ex = None
    try:
        code = compile(src, '<input>', 'exec')
        exec(code)
    except Exception as exc:
        ex = BuildError.from_exception(exc, sources={'<input>': src})
    return ex


def meta_executor(src, level=1):
    if level <= 1:
        return executor(src)
    else:
        return meta_executor(src, level - 1)


def test_traceback_starts_at_the_right_level():
    ex = meta_executor('1/0')
    assert isinstance(ex, BuildError)
    assert ex.message == """Traceback (most recent call last):
  File "<input>", line 1, in <module>
    1/0
ZeroDivisionError: division by zero
"""
