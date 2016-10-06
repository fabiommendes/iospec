from iospec import isequal, parse, testcase_diff as _testcase_diff, In, IoSpec
from iospec.datatypes.node import Node
from iospec.utils import indent
from .test_iospec import spec1 as spec1, spec2


src1 = """
<foo>
<bar>
foobar
"""

src1b = """# comment
<foo>
<bar>
foobar
"""

src2 = """
<foo>
<foo>
foofoo
"""


class TestIsEqualFunction:
    def test_io_equal(self, spec1, spec2):
        assert isequal(spec1, spec1)
        assert isequal(spec2, spec2)
        assert not isequal(spec1, spec2)

    def test_io_equal_presentation(self, spec1, spec2):
        assert isequal(spec1, spec2, casefold=True, skip_spaces=True)


def test_node_equality():
    assert Node([In('foo')]) == Node([In('foo')])
    assert IoSpec() == IoSpec()


def test_case_diff():
    tc1 = parse(src1)[0]
    tc2 = parse(src1b)[0]

    diff = _testcase_diff(tc1, tc2)
    assert not diff.is_different
    assert str(diff) == indent(src1.strip(), 4)


def test_case_diff_2():
    tc1 = parse(src1)[0]
    tc2 = parse(src2)[0]

    diff = _testcase_diff(tc1, tc2)
    assert diff.is_different
    print(diff)
    assert str(diff) == """    <foo>
----
-   <bar>
+   <foo>
different-lines"""
