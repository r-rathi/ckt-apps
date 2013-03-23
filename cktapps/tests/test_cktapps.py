""" Test cktapps """

import pytest
from StringIO import StringIO
from collections import OrderedDict

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
        tokens = spice.split_spice_line(line)
        assert tokens == ['a1', 'a2', 'a3']

    def test_kwargs(self):
        line = 'a1 a2  k1=v1 k2= v2 k3 =v3 k4 = v4'
        tokens = spice.split_spice_line(line)
        assert tokens == ['a1', 'a2', 'k1', '=', 'v1', 'k2', '=', 'v2',
                          'k3', '=', 'v3', 'k4', '=', 'v4']

    def test_kwargs_exp(self):
        line = 'a1 a2  k1=" 1* 2" k2 = " (1 + v2) " k3 = 3.0p k4= v4 '
        tokens = spice.split_spice_line(line)
        assert tokens == ['a1', 'a2', 'k1', '=', '"1*2"', 'k2', '=', '"(1+v2)"',
                          'k3', '=', '3.0p', 'k4', '=', 'v4']

    def test_blank_line(self):
        line = '  '
        tokens = spice.split_spice_line(line)
        assert tokens == []

    def test_comment_line(self):
        line = '* ab c  '
        tokens = spice.split_spice_line(line)
        assert tokens == ['*', 'ab', 'c']

        line = ' * ab c  '
        tokens = spice.split_spice_line(line)
        assert tokens == ['*', 'ab', 'c']

        line = '*ab c  '
        tokens = spice.split_spice_line(line)
        assert tokens == ['*', 'ab', 'c']

        line = '$ ab c  '
        tokens = spice.split_spice_line(line)
        assert tokens == ['$', 'ab', 'c']

    def test_tailing_comment(self):
        line = 'ab $ c d'
        tokens = spice.split_spice_line(line)
        assert tokens == ['ab', '$', 'c', 'd']

        line = 'ab $c d'
        tokens = spice.split_spice_line(line)
        assert tokens == ['ab', '$', 'c', 'd']

        line = 'ab$ c d'
        tokens = spice.split_spice_line(line)
        assert tokens == ['ab', '$', 'c', 'd']

        line = 'ab$c d'
        tokens = spice.split_spice_line(line)
        assert tokens == ['ab', '$', 'c', 'd']


class TestSpiceParseLine:
    #@classmethod
    #def setup_class(cls):
        #pass
    #@classmethod
    #def teardown_class(cls):
        #pass

    def test_element_args(self):
        tokens = 'm a1 a2 a3'.split()
        parsed = spice.parse_spice_line(tokens)
        assert parsed == {'type'   : ['element', 'm'],
                          'args'   : ['m', 'a1', 'a2', 'a3'],
                          'kwargs' : OrderedDict()
                         }

        tokens = 'mxy a1 a2 a3'.split()
        parsed = spice.parse_spice_line(tokens)
        assert parsed == {'type'   : ['element', 'm'],
                          'args'   : ['mxy', 'a1', 'a2', 'a3'],
                          'kwargs' : OrderedDict()
                         }

    def test_control_args(self):
        tokens = '.subckt a1 a2 a3'.split()
        parsed = spice.parse_spice_line(tokens)
        assert parsed == {'type'   : ['control', 'subckt'],
                          'args'   : ['.subckt', 'a1', 'a2', 'a3'],
                          'kwargs' : OrderedDict()
                         }

    def test_element_kwargs1(self):
        tokens = 'mxy a1 a2 kw1 = v1'.split()
        parsed = spice.parse_spice_line(tokens)
        assert parsed == {'type'   : ['element', 'm'],
                          'args'   : ['mxy', 'a1', 'a2'],
                          'kwargs' : OrderedDict(kw1='v1')
                         }

    def test_element_kwargs2(self):
        tokens = 'mxy a1 a2 kw1 = v1 kw2 = v2'.split()
        parsed = spice.parse_spice_line(tokens)
        assert parsed == {'type'   : ['element', 'm'],
                          'args'   : ['mxy', 'a1', 'a2'],
                          'kwargs' : OrderedDict(kw1='v1', kw2='v2')
                         }

    def test_control_kwargs2(self):
        tokens = '.subckt a1 a2 kw1 = v1 kw2 = v2'.split()
        parsed = spice.parse_spice_line(tokens)
        assert parsed == {'type'   : ['control', 'subckt'],
                          'args'   : ['.subckt', 'a1', 'a2'],
                          'kwargs' : OrderedDict(kw1='v1', kw2='v2')
                         }

    def test_control_kwargs_only(self):
        tokens = '.subckt kw1 = v1 kw2 = v2'.split()
        parsed = spice.parse_spice_line(tokens)
        assert parsed == {'type'   : ['control', 'subckt'],
                          'args'   : ['.subckt'],
                          'kwargs' : OrderedDict(kw1='v1', kw2='v2')
                         }

    def test_control_kwargs_bad1(self):
        tokens = '.subckt kw1 = v1 a1 kw2 = v2'.split()
        with pytest.raises(spice.SyntaxError) as e:
            parsed = spice.parse_spice_line(tokens)
        assert e.value.message == "unexpected token 'kw2' at pos '6'"

    def test_control_kwargs_bad2(self):
        tokens = '.subckt kw1 = v1 kw2 ='.split()
        with pytest.raises(spice.SyntaxError) as e:
            parsed = spice.parse_spice_line(tokens)
        assert e.value.message == "unexpected token '=' at pos '6'"

    def test_control_kwargs_bad3(self):
        tokens = '.subckt kw1 = v1 kw2'.split()
        with pytest.raises(spice.SyntaxError) as e:
            parsed = spice.parse_spice_line(tokens)
        assert e.value.message == "unexpected token 'kw2' at pos '5'"
