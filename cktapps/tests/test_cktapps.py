""" Test cktapps """

import pytest
from StringIO import StringIO

from cktapps.formats import spice

class TestSpiceReadLine:
    def test_simple(self):
        f = StringIO("a b\n"
                     "* c\n"
                     "  d $ e")
        f.name = "<string>"

        lines = [line for line in spice.read_spice_line(f)]

        assert lines[0] == ("a b",     "<string>", 1)
        assert lines[1] == ("* c",     "<string>", 2)
        assert lines[2] == ("  d $ e", "<string>", 3)

    def test_unwrap_single(self):
        f = StringIO("a b\n"
                     "+ c\n"
                     "  d $ e")
        f.name = "<string>"

        lines = [line for line in spice.read_spice_line(f)]

        assert lines[0] == ("a b c",     "<string>", 2)
        assert lines[1] == ("  d $ e",   "<string>", 3)

    def test_unwrap_multi(self):
        f = StringIO("a b \n"
                     "+ c1\n"
                     "+c2\n"
                     "+  c3\n"
                     "  d $ e")
        f.name = "<string>"

        lines = [line for line in spice.read_spice_line(f)]

        assert lines[0] == ("a b c1 c2 c3", "<string>", 4)
        assert lines[1] == ("  d $ e",      "<string>", 5)

    def test_unwrap_blank_line(self):
        f = StringIO("a b\n"
                     "c1\n"
                     " \n"
                     "+ c2\n"
                     "  d $ e")
        f.name = "<string>"

        with pytest.raises(spice.SyntaxError) as e:
            lines = [line for line in spice.read_spice_line(f)]

        assert e.value.message == "invalid line continuation: <string>, 4\n+ c2"

    def test_unwrap_leading_comment(self):
        f = StringIO("a b\n"
                     "c1\n"
                     "* comment\n"
                     "+ c2\n"
                     "  d $ e")
        f.name = "<string>"

        with pytest.raises(spice.SyntaxError) as e:
            lines = [line for line in spice.read_spice_line(f)]

        assert e.value.message == "invalid line continuation: <string>, 4\n+ c2"

    def test_unwrap_trailing_comment(self):
        f = StringIO("a b\n"
                     "c1 $comment\n"
                     "+ c2\n"
                     "  d $ e")
        f.name = "<string>"

        with pytest.raises(spice.SyntaxError) as e:
            lines = [line for line in spice.read_spice_line(f)]

        assert e.value.message == "invalid line continuation: <string>, 3\n+ c2"

class TestSpiceSplitLine:
    def test_args(self):
        line = 'a1 a2  a3'
        parsed = spice.split_spice_line(line)
        assert parsed == ['a1', 'a2', 'a3']

    def test_kwargs(self):
        line = 'a1 a2  k1=v1 k2= v2 k3 =v3 k4 = v4'
        parsed = spice.split_spice_line(line)
        assert parsed == ['a1', 'a2', 'k1', '=', 'v1', 'k2', '=', 'v2',
                          'k3', '=', 'v3', 'k4', '=', 'v4']

    def test_kwargs_exp(self):
        line = 'a1 a2  k1=" 1* 2" k2 = " (1 + v2) " k3 = 3.0p k4= v4 '
        parsed = spice.split_spice_line(line)
        assert parsed == ['a1', 'a2', 'k1', '=', '"1*2"', 'k2', '=', '"(1+v2)"',
                          'k3', '=', '3.0p', 'k4', '=', 'v4']

    def test_blank_line(self):
        line = '  '
        parsed = spice.split_spice_line(line)
        assert parsed == []

    def test_comment_line(self):
        line = '* ab c  '
        parsed = spice.split_spice_line(line)
        assert parsed == ['*', 'ab', 'c']

        line = ' * ab c  '
        parsed = spice.split_spice_line(line)
        assert parsed == ['*', 'ab', 'c']

        line = '*ab c  '
        parsed = spice.split_spice_line(line)
        assert parsed == ['*', 'ab', 'c']

        line = '$ ab c  '
        parsed = spice.split_spice_line(line)
        assert parsed == ['$', 'ab', 'c']

    def test_tailing_comment(self):
        line = 'ab $ c d'
        parsed = spice.split_spice_line(line)
        assert parsed == ['ab', '$', 'c', 'd']

        line = 'ab $c d'
        parsed = spice.split_spice_line(line)
        assert parsed == ['ab', '$', 'c', 'd']

        line = 'ab$ c d'
        parsed = spice.split_spice_line(line)
        assert parsed == ['ab', '$', 'c', 'd']

        line = 'ab$c d'
        parsed = spice.split_spice_line(line)
        assert parsed == ['ab', '$', 'c', 'd']


#class TestParseLine:
    #@classmethod
    #def setup_class(cls):
        #pass
    #@classmethod
    #def teardown_class(cls):
        #pass
