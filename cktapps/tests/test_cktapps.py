""" Test cktapps """

import pytest
from StringIO import StringIO
from collections import OrderedDict

from cktapps import core
from cktapps import Ckt
from cktapps.formats import spice

class TestSpiceReadLine:
    def test_simple(self):
        f = StringIO("a b\n"
                     "* c\n"
                     "  d $ e")
        f.name = "<string>"

        lines = [line for line in spice.Reader.read_line(f)]

        assert lines[0] == ("a b",     "<string>", 1)
        assert lines[1] == ("* c",     "<string>", 2)
        assert lines[2] == ("  d $ e", "<string>", 3)

    def test_unwrap_single(self):
        f = StringIO("a b\n"
                     "+ c\n"
                     "  d $ e")
        f.name = "<string>"

        lines = [line for line in spice.Reader.read_line(f)]

        assert lines[0] == ("a b c",     "<string>", 2)
        assert lines[1] == ("  d $ e",   "<string>", 3)

    def test_unwrap_multi(self):
        f = StringIO("a b \n"
                     "+ c1\n"
                     "+c2\n"
                     "+  c3\n"
                     "  d $ e")
        f.name = "<string>"

        lines = [line for line in spice.Reader.read_line(f)]

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
            lines = [line for line in spice.Reader.read_line(f)]

        assert e.value.message == "invalid line continuation: <string>, 4\n-> + c2"

    def test_unwrap_leading_comment(self):
        f = StringIO("a b\n"
                     "c1\n"
                     "* comment\n"
                     "+ c2\n"
                     "  d $ e")
        f.name = "<string>"

        with pytest.raises(spice.SyntaxError) as e:
            lines = [line for line in spice.Reader.read_line(f)]

        assert e.value.message == "invalid line continuation: <string>, 4\n-> + c2"

    def test_unwrap_trailing_comment(self):
        f = StringIO("a b\n"
                     "c1 $comment\n"
                     "+ c2\n"
                     "  d $ e")
        f.name = "<string>"

        with pytest.raises(spice.SyntaxError) as e:
            lines = [line for line in spice.Reader.read_line(f)]

        assert e.value.message == "invalid line continuation: <string>, 3\n-> + c2"

class TestSpiceSplitLine:
    def test_args(self):
        line = 'a1 a2  a3'
        tokens = spice.Reader._tokenize(line)
        assert tokens == ['a1', 'a2', 'a3']

    def test_kwargs(self):
        line = 'a1 a2  k1=v1 k2= v2 k3 =v3 k4 = v4'
        tokens = spice.Reader._tokenize(line)
        assert tokens == ['a1', 'a2', 'k1=v1', 'k2=v2',
                          'k3=v3', 'k4=v4']

    def test_kwargs_exp(self):
        line = 'a1 a2  k1=" 1* 2" k2 = " (1 + v2) " k3 = 3.0p k4= v4 '
        tokens = spice.Reader._tokenize(line)
        assert tokens == ['a1', 'a2', 'k1="1*2"', 'k2="(1+v2)"',
                          'k3=3.0p', 'k4=v4']

    def test_blank_line(self):
        line = '  '
        tokens = spice.Reader._tokenize(line)
        assert tokens == []

    def test_comment_line(self):
        line = '* ab c  '
        tokens = spice.Reader._tokenize(line)
        assert tokens == ['*', 'ab', 'c']

        line = ' * ab c  '
        tokens = spice.Reader._tokenize(line)
        assert tokens == ['*', 'ab', 'c']

        line = '*ab c  '
        tokens = spice.Reader._tokenize(line)
        assert tokens == ['*', 'ab', 'c']

        line = '$ ab c  '
        tokens = spice.Reader._tokenize(line)
        assert tokens == ['$', 'ab', 'c']

    def test_tailing_comment(self):
        line = 'ab $ c d'
        tokens = spice.Reader._tokenize(line)
        assert tokens == ['ab', '$', 'c', 'd']

        line = 'ab $c d'
        tokens = spice.Reader._tokenize(line)
        assert tokens == ['ab', '$', 'c', 'd']

        line = 'ab$ c d'
        tokens = spice.Reader._tokenize(line)
        assert tokens == ['ab', '$', 'c', 'd']

        line = 'ab$c d'
        tokens = spice.Reader._tokenize(line)
        assert tokens == ['ab', '$', 'c', 'd']

    def test_kwarg_tailing_comment(self):
        line = 'ab c=$d'
        tokens = spice.Reader._tokenize(line)
        assert tokens == ['ab', 'c=', '$', 'd']


class TestSpiceParseLine:
    def test_element_args(self):
        tokens = 'm a1 a2 a3'.split()
        parsed = spice.Reader._parse(tokens)
        assert parsed == {'type'   : ['element', 'm'],
                          'args'   : ['m', 'a1', 'a2', 'a3'],
                          'kwargs' : OrderedDict(),
                          'comment': ''
                         }

        tokens = 'mxy a1 a2 a3'.split()
        parsed = spice.Reader._parse(tokens)
        assert parsed == {'type'   : ['element', 'm'],
                          'args'   : ['mxy', 'a1', 'a2', 'a3'],
                          'kwargs' : OrderedDict(),
                          'comment': ''
                         }

    def test_control_args(self):
        tokens = '.subckt a1 a2 a3'.split()
        parsed = spice.Reader._parse(tokens)
        assert parsed == {'type'   : ['control', 'subckt'],
                          'args'   : ['.subckt', 'a1', 'a2', 'a3'],
                          'kwargs' : OrderedDict(),
                          'comment': ''
                         }

    def test_element_kwargs1(self):
        tokens = 'mxy a1 a2 kw1=v1'.split()
        parsed = spice.Reader._parse(tokens)
        assert parsed == {'type'   : ['element', 'm'],
                          'args'   : ['mxy', 'a1', 'a2'],
                          'kwargs' : OrderedDict(kw1='v1'),
                          'comment': ''
                         }

    def test_element_kwargs2(self):
        tokens = 'mxy a1 a2 kw1=v1 kw2=v2'.split()
        parsed = spice.Reader._parse(tokens)
        assert parsed == {'type'   : ['element', 'm'],
                          'args'   : ['mxy', 'a1', 'a2'],
                          'kwargs' : OrderedDict(kw1='v1', kw2='v2'),
                          'comment': ''
                         }

    def test_control_kwargs2(self):
        tokens = '.subckt a1 a2 kw1=v1 kw2=v2'.split()
        parsed = spice.Reader._parse(tokens)
        assert parsed == {'type'   : ['control', 'subckt'],
                          'args'   : ['.subckt', 'a1', 'a2'],
                          'kwargs' : OrderedDict(kw1='v1', kw2='v2'),
                          'comment': ''
                         }

    def test_control_kwargs_only(self):
        tokens = '.subckt kw1=v1 kw2=v2'.split()
        parsed = spice.Reader._parse(tokens)
        assert parsed == {'type'   : ['control', 'subckt'],
                          'args'   : ['.subckt'],
                          'kwargs' : OrderedDict(kw1='v1', kw2='v2'),
                          'comment': ''
                         }

    def test_control_kwargs_bad1(self):
        tokens = '.subckt kw1=v1 a1 kw2=v2'.split()
        with pytest.raises(spice.SyntaxError) as e:
            parsed = spice.Reader._parse(tokens)
        #assert e.value.message == "unexpected token 'kw2' at pos '6'"
        assert e.value.message == "unexpected token 'a1' at pos '2'"

    def test_control_kwargs_bad2(self):
        tokens = '.subckt kw1=v1 kw2='.split()
        with pytest.raises(spice.SyntaxError) as e:
            parsed = spice.Reader._parse(tokens)
        #assert e.value.message == "unexpected token '=' at pos '6'"
        assert e.value.message == "missing parameter value: kw2=?"

    def test_control_kwargs_bad3(self):
        tokens = '.subckt kw1=v1 kw2'.split()
        with pytest.raises(spice.SyntaxError) as e:
            parsed = spice.Reader._parse(tokens)
        #assert e.value.message == "unexpected token 'kw2' at pos '5'"
        assert e.value.message == "unexpected token 'kw2' at pos '2'"

    def test_comment_line_skip_true(self):
        tokens = '* mxy a1 a2 kw1=v1'.split()
        parsed = spice.Reader._parse(tokens)
        assert parsed is None
        #assert parsed == {'type'   : ['comment', '*'],
        #                  'args'   : [],
        #                  'kwargs' : {},
        #                  'comment': '* mxy a1 a2 kw1=v1'
        #                 }

    def test_comment_line_skip_false(self):
        tokens = '* mxy a1 a2 kw1=v1'.split()
        parsed = spice.Reader._parse(tokens, skipcomments=False)
        assert parsed == {'type'   : ['comment', '*'],
                          'args'   : [],
                          'kwargs' : {},
                          'comment': '* mxy a1 a2 kw1=v1'
                         }

    def test_trailing_comment_skip_true(self):
        tokens = 'mxy a1 a2 kw1=v1 $ c1 c2'.split()
        parsed = spice.Reader._parse(tokens)
        assert parsed == {'type'   : ['element', 'm'],
                          'args'   : ['mxy', 'a1', 'a2'],
                          'kwargs' : OrderedDict(kw1='v1'),
                          'comment': '$ c1 c2'
                         }

    def test_trailing_comment_skip_false(self):
        tokens = 'mxy a1 a2 kw1=v1 $ c1 c2'.split()
        parsed = spice.Reader._parse(tokens, skipcomments=False)
        assert parsed == {'type'   : ['element', 'm'],
                          'args'   : ['mxy', 'a1', 'a2'],
                          'kwargs' : OrderedDict(kw1='v1'),
                          'comment': '$ c1 c2'
                         }

class TestSpiceMacromodel:
    def test_simple(self):
        f = StringIO(
            """
.macromodel nch_mac nmos d g s b w=1 l=1
+ cg="w * l * 0.05" $ gate cap (F)
            """)
        f.name = "<string>"

        ckt = Ckt()
        ckt.read_spice(f)

        assert ckt.prims.get('nch_mac').name == 'nch_mac'
        assert ckt.prims.get('nch_mac').type == 'nmos'
        assert ckt.prims.get('nch_mac').portnames == ['d', 'g', 's', 'b']

class TestCktObj:
    def test_name(self):
        obj = core.CktObj(name="myname")
        assert obj.name == "myname"
        assert obj.container is None

class TestCktObjContainer:
    def test_add(self):
        objcont = core.CktObjContainer(objtype=core.CktObj, owner="myowner")
        obj = objcont.add(name="myname")
        assert obj.name == "myname"
        assert obj.container.owner is "myowner"

    def test_addobj(self):
        objcont = core.CktObjContainer(objtype=core.CktObj, owner="myowner")
        obj = core.CktObj(name="myname")
        assert objcont.addobj(obj) is obj
        assert obj.container.owner is "myowner"

    def test_addobj_noname(self):
        objcont = core.CktObjContainer(objtype=core.CktObj, owner="myowner")
        obj = core.CktObj(name=None)
        with pytest.raises(core.CktObjValueError) as e:
            objcont.addobj(obj)

    def test_addobj_badobj(self):
        objcont = core.CktObjContainer(objtype=core.CktObj, owner="myowner")
        class BadCktObj: pass
        badobj = BadCktObj()
        with pytest.raises(core.CktObjTypeError) as e:
            objcont.addobj(badobj)

    def test_get(self):
        objcont = core.CktObjContainer(objtype=core.CktObj, owner="myowner")
        obj1 = objcont.add(name="name1")
        obj2 = objcont.add(name="name2")
        assert objcont.get("name1") is obj1
        assert objcont.get("name2") is obj2

    def test_get_missing(self):
        objcont = core.CktObjContainer(objtype=core.CktObj, owner="myowner")
        obj1 = objcont.add(name="name1")
        with pytest.raises(core.CktObjDoesNotExist) as e:
            objcont.get("name2")

    def test_get_default(self):
        objcont = core.CktObjContainer(objtype=core.CktObj, owner="myowner")
        obj1 = objcont.add(name="name1")
        assert objcont.get_default("name2") is None
        assert objcont.get_default("name2", obj1) is obj1

    def test_all(self):
        objcont = core.CktObjContainer(objtype=core.CktObj, owner="myowner")
        obj1 = objcont.add(name="name1")
        obj2 = objcont.add(name="name2")
        assert list(objcont.all()) == [obj1, obj2]

    def test_filter(self):
        objcont = core.CktObjContainer(objtype=core.CktObj, owner="myowner")
        obj1 = objcont.add(name="name1")
        obj2 = objcont.add(name="name2")
        objx1 = objcont.add(name="obx1")
        objx2 = objcont.add(name="objx2")
        assert list(objcont.filter(name="name.*")) == [obj1, obj2]
        assert list(objcont.filter(name=".*x.")) == [objx1, objx2]
        assert list(objcont.filter(name=".*1")) == [obj1, objx1]


