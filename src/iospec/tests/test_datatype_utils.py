from iospec import isequal, In, IoSpec
from iospec.datatypes.node import Node
from .test_iospec import spec1, spec2


class TestIsEqualFunction:
    def test_io_equal(self, spec1, spec2):
        assert isequal(spec1, spec1)
        assert isequal(spec2, spec2)
        assert not isequal(spec1, spec2)

    def test_io_equal_presentation(self, spec1, spec2):
        assert isequal(spec1, spec2, presentation=True)


def test_node_equality():
    assert Node([In('foo')]) == Node([In('foo')])
    assert IoSpec() == IoSpec()