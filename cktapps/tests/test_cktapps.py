""" Test cktapps """

import pytest
from StringIO import StringIO

from cktapps.formats import spice

class TestSpiceReadLine:
    def test_simple(self):
        file = StringIO("a b\n"
                        "* c\n"
                        "  d $ e")
        file.name = "<string>"

        lines = [line for line in spice.read_spice_line(file)]

        assert lines[0] == ("a b",     "<string>", 1)
        assert lines[1] == ("* c",     "<string>", 2)
        assert lines[2] == ("  d $ e", "<string>", 3)

    def test_unwrap_single(self):
        file = StringIO("a b\n"
                        "+ c\n"
                        "  d $ e")
        file.name = "<string>"

        lines = [line for line in spice.read_spice_line(file)]

        assert lines[0] == ("a b c",     "<string>", 2)
        assert lines[1] == ("  d $ e",   "<string>", 3)

    def test_unwrap_multi(self):
        file = StringIO("a b \n"
                        "+ c1\n"
                        "+c2\n"
                        "+  c3\n"
                        "  d $ e")
        file.name = "<string>"

        lines = [line for line in spice.read_spice_line(file)]

        assert lines[0] == ("a b c1 c2 c3", "<string>", 4)
        assert lines[1] == ("  d $ e",      "<string>", 5)
    def test_unwrap_blank_line(self):
        file = StringIO("a b\n"
                        "c1\n"
                        " \n"
                        "+ c2\n"
                        "  d $ e")
        file.name = "<string>"

        with pytest.raises(spice.SyntaxError) as e:
            lines = [line for line in spice.read_spice_line(file)]

        assert e.value.message == "invalid line continuation: <string>, 4\n+ c2"

    def test_unwrap_leading_comment(self):
        file = StringIO("a b\n"
                        "c1\n"
                        "* comment\n"
                        "+ c2\n"
                        "  d $ e")
        file.name = "<string>"

        with pytest.raises(spice.SyntaxError) as e:
            lines = [line for line in spice.read_spice_line(file)]

        assert e.value.message == "invalid line continuation: <string>, 4\n+ c2"

    def test_unwrap_trailing_comment(self):
        file = StringIO("a b\n"
                        "c1 $comment\n"
                        "+ c2\n"
                        "  d $ e")
        file.name = "<string>"

        with pytest.raises(spice.SyntaxError) as e:
            lines = [line for line in spice.read_spice_line(file)]

        assert e.value.message == "invalid line continuation: <string>, 3\n+ c2"

