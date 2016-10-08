from iospec import parse, Command
from iospec.commands import all as cmd
from iospec.commands.utils import parse_number


def test_fake_commands():
    c = cmd.Fake('email')
    assert '@' in c.generate()


def test_fake_string_limit():
    for cls in [cmd.Name, cmd.FirstName, cmd.LastName, cmd.Str, cmd.Text,
                cmd.Paragraph]:
        c = cls(10)
        assert len(c.generate()) <= 10


def test_parse_number():
    func = lambda x: parse_number(x, int, -128, 127)

    assert func('') == (-128, 127)
    assert func('+') == (0, 127)
    assert func('-') == (-128, 0)
    assert func('++') == (1, 127)
    assert func('--') == (-128, -1)
    assert func('+10') == (0, 10)
    assert func('-10') == (-10, 0)
    assert func('10') == (-10, 10)
    assert func('10..20') == (10, 20)
    assert func('10:20') == (10, 19)


def test_integers():
    assert -10 <= cmd.Int(10).generate() <= 10
    assert 0 <= cmd.Int(0, 10).generate() <= 10


def test_digits():
    assert 0 <= cmd.Digit().generate() <= 9


def test_floats():
    assert -10 <= cmd.Float(10).generate() <= 10
    assert 0 <= cmd.Float(0, 10).generate() <= 10


def test_small_float():
    assert 0 <= cmd.SmallFloat().generate() <= 1


def test_simple_command_iospec_source():
    out, in_ = parse('foo: $int')[0]
    assert out == 'foo: '
    assert isinstance(in_, Command)
    assert isinstance(in_.generate(), int)


def test_command_with_arguments_from_iospec_source():
    out, in_ = parse('foo: $int(0, 10)')[0]
    assert out == 'foo: '
    assert isinstance(in_, Command)
    assert isinstance(in_.generate(), int)
    assert in_.generate() >= 0
    assert in_.generate() <= 10
