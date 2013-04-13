""" Test cktapps """

import pytest
from StringIO import StringIO
from collections import OrderedDict
from textwrap import dedent

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

    def test_kwargs_exp1(self):
        line = 'a1 a2  k1=" 1* 2" k2 = " (1 + v2) " k3 = 3.0p k4= v4 '
        tokens = spice.Reader._tokenize(line)
        assert tokens == ['a1', 'a2', 'k1=1*2', 'k2=(1+v2)',
                          'k3=3.0p', 'k4=v4']

    def test_kwargs_exp2(self):
        line = 'a1 a2  k1=\' 1* 2\' k2 = " (1 + v2) " k3 = \'3.0p \' k4= v4 '
        tokens = spice.Reader._tokenize(line)
        assert tokens == ['a1', 'a2', 'k1=1*2', 'k2=(1+v2)',
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

    def test_spice_units1(self):
        tokens = 'mxy a1 a2 kw1=1.0e-15 kw2=1ff'.split()
        parsed = spice.Reader._parse(tokens)
        assert parsed == {'type'   : ['element', 'm'],
                          'args'   : ['mxy', 'a1', 'a2'],
                          'kwargs' : OrderedDict(kw1='1.0e-15', kw2='1e-15'),
                          'comment': ''
                         }

    def test_spice_units2(self):
        tokens = 'mxy a1 a2 kw1=1.0p kw2=(1m*1p)+1e-15'.split()
        parsed = spice.Reader._parse(tokens)
        assert parsed == {'type'   : ['element', 'm'],
                          'args'   : ['mxy', 'a1', 'a2'],
                          'kwargs' : OrderedDict(kw1='1e-12',
                                                 kw2='(0.001*1e-12)+1e-15'),
                          'comment': ''
                         }

class TestSpiceMacromodel:
    def test_simple(self):
        f = StringIO(dedent(
            """\
            .macromodel nch_mac nmos d g s b w=1 l=1
            + cg="w * l * 0.05" $ gate cap (F)
            """))
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


class TestL0HierarchicalParams:
    def make_ckt(self):
        f = StringIO(dedent(
            """\
            .macromodel pch_mac pmos d g s b m=1 cg="m*w*l*0.05"
            .macromodel nch_mac nmos d g s b m=1 cg="m*w*l*0.05"

            .subckt pinv a y vdd vss w=2 l=2.0
            xmp y a vdd vdd pch_mac w="2*W" l=1.0
            xmn y a vss vss nch_mac W=w     l=1.0
            .ends
            """))
        f.name = "<string>"
        ckt = Ckt()
        ckt.read_spice(f)
        return ckt

    def test_param_value(self):
        ckt = self.make_ckt()
        pinv = ckt.get_cell('pinv')
        assert pinv.get_param('w').value == '2'
        assert pinv.get_param('l').value == '2.0'
        xmp = pinv.get_instance('mp')
        assert xmp.get_param('w').value == '2*w'
        assert xmp.get_param('l').value == '1.0'
        xmn = pinv.get_instance('mn')
        assert xmn.get_param('w').value == 'w'
        assert xmn.get_param('l').value == '1.0'

    def test_cell_param_eval(self):
        ckt = self.make_ckt()
        pinv = ckt.get_cell('pinv')
        assert pinv.eval_param('w') == 2.0
        assert pinv.eval_param('l') == 2.0

    def test_inst_param_eval(self):
        ckt = self.make_ckt()
        pinv = ckt.get_cell('pinv')
        pinv.link()
        xmp = pinv.get_instance('mp')
        assert xmp.eval_param('w') == 4.0
        assert xmp.eval_param('l') == 1.0
        xmn = pinv.get_instance('mn')
        assert xmn.eval_param('w') == 2.0
        assert xmn.eval_param('l') == 1.0

    def test_ref_param_eval(self):
        ckt = self.make_ckt()
        pinv = ckt.get_cell('pinv')
        pinv.link()
        xmp = pinv.get_instance('mp')
        assert xmp.eval_ref_param('w') == 4.0
        assert xmp.eval_ref_param('l') == 1.0
        assert xmp.ref.get_param('cg').value == 'm*w*l*0.05'
        assert xmp.eval_ref_param('cg') == 0.2
        xmn = pinv.get_instance('mn')
        assert xmn.eval_ref_param('w') == 2.0
        assert xmn.eval_ref_param('l') == 1.0
        assert xmn.ref.get_param('cg').value == 'm*w*l*0.05'
        assert xmn.eval_ref_param('cg') == 0.1

class TestL1HierarchicalParams:
    def make_ckt(self):
        f = StringIO(dedent(
            """\
            .macromodel pch_mac pmos d g s b m=1 cg="m*w*l*0.05"
            .macromodel nch_mac nmos d g s b m=1 cg="m*w*l*0.05"

            .subckt pinv a y vdd vss w=2 l=2.0
            xmp y a vdd vdd pch_mac w="2*W" l=1.0
            xmn y a vss vss nch_mac W=w     l=1.0
            .ends

            .subckt buf a y vdd vss
            xi1 a n vdd vss pinv
            xi2 n y vdd vss pinv
            .ends
            """))
        f.name = "<string>"
        ckt = Ckt()
        ckt.read_spice(f)
        return ckt

    def test_non_hier_ref_param_eval(self):
        ckt = self.make_ckt()
        pinv = ckt.get_cell('pinv')
        pinv.link()
        xmp = pinv.get_instance('mp')
        assert xmp.ref.get_param('cg').value == 'm*w*l*0.05'
        assert xmp.eval_ref_param('cg') == 0.2
        xmn = pinv.get_instance('mn')
        assert xmn.ref.get_param('cg').value == 'm*w*l*0.05'
        assert xmn.eval_ref_param('cg') == 0.1

    def test_hier_ref_param_eval(self):
        ckt = self.make_ckt()
        buf = ckt.get_cell('buf')
        buf.link()
        xi1 = buf.get_instance('i1')
        assert xi1.ref.get_param('w').value == '2'
        assert xi1.eval_ref_param('w') == 2.0
        assert xi1.eval_ref_param('l') == 2.0
        xi2 = buf.get_instance('i2')
        assert xi2.ref.get_param('w').value == '2'
        assert xi2.eval_ref_param('w') == 2.0
        assert xi1.eval_ref_param('l') == 2.0

    def test_hier_flatten_param_eval(self):
        ckt = self.make_ckt()
        buf = ckt.get_cell('buf')
        buf.link()
        buf.ungroup(flatten=True)

        xi1_mp = buf.get_instance('i1/mp')
        assert xi1_mp.get_param('w').value == '2*w'
        assert xi1_mp.eval_ref_param('w') == 4.0
        assert xi1_mp.eval_ref_param('l') == 1.0
        assert xi1_mp.eval_ref_param('cg') == 0.2

        xi1_mn = buf.get_instance('i1/mn')
        assert xi1_mn.get_param('w').value == 'w'
        assert xi1_mn.eval_ref_param('w') == 2.0
        assert xi1_mn.eval_ref_param('l') == 1.0
        assert xi1_mn.eval_ref_param('cg') == 0.1

        xi2_mp = buf.get_instance('i2/mp')
        assert xi2_mp.get_param('w').value == '2*w'
        assert xi2_mp.eval_ref_param('w') == 4.0
        assert xi2_mp.eval_ref_param('l') == 1.0
        assert xi2_mp.eval_ref_param('cg') == 0.2

        xi2_mn = buf.get_instance('i2/mn')
        assert xi2_mn.get_param('w').value == 'w'
        assert xi2_mn.eval_ref_param('w') == 2.0
        assert xi2_mn.eval_ref_param('l') == 1.0
        assert xi2_mn.eval_ref_param('cg') == 0.1

class TestL2HierarchicalParams:
    def make_ckt(self):
        f = StringIO(dedent(
            """\
            .macromodel pch_mac pmos d g s b m=1 cg="m*w*l*0.05"
            .macromodel nch_mac nmos d g s b m=1 cg="m*w*l*0.05"

            .subckt pinv a y vdd vss w=2 l=2.0
            xmp y a vdd vdd pch_mac w="2*W" l=1.0
            xmn y a vss vss nch_mac W=w     l=1.0
            .ends

            .subckt buf a y vdd vss
            xi1 a n vdd vss pinv
            xi2 n y vdd vss pinv w=3 l=3 
            xi3 n y vdd vss pinv w=5 l=5
            .ends
            """))
        f.name = "<string>"
        ckt = Ckt()
        ckt.read_spice(f)
        return ckt

    def test_hier_flatten_param_eval(self):
        ckt = self.make_ckt()
        buf = ckt.get_cell('buf')
        buf.link()
        buf.ungroup(flatten=True)

        xi1_mp = buf.get_instance('i1/mp')
        assert xi1_mp.get_param('w').value == '2*w'
        assert xi1_mp.eval_ref_param('w') == 4.0
        assert xi1_mp.eval_ref_param('l') == 1.0
        assert xi1_mp.eval_ref_param('cg') == 0.2
        xi1_mn = buf.get_instance('i1/mn')
        assert xi1_mn.get_param('w').value == 'w'
        assert xi1_mn.eval_ref_param('w') == 2.0
        assert xi1_mn.eval_ref_param('l') == 1.0
        assert xi1_mn.eval_ref_param('cg') == 0.1

        xi2_mp = buf.get_instance('i2/mp')
        assert xi2_mp.get_param('w').value == '2*w'
        assert xi2_mp.eval_ref_param('w') == 6.0
        assert xi2_mp.eval_ref_param('l') == 1.0
        assert abs(xi2_mp.eval_ref_param('cg') - 0.3) < 1e-6
        xi2_mn = buf.get_instance('i2/mn')
        assert xi2_mn.get_param('w').value == 'w'
        assert xi2_mn.eval_ref_param('w') == 3.0
        assert xi2_mn.eval_ref_param('l') == 1.0
        assert abs(xi2_mn.eval_ref_param('cg') - 0.15) < 1e-6

        xi3_mp = buf.get_instance('i3/mp')
        assert xi3_mp.get_param('w').value == '2*w'
        assert xi3_mp.eval_ref_param('w') == 10.0
        assert xi3_mp.eval_ref_param('l') == 1.0
        assert abs(xi3_mp.eval_ref_param('cg') - 0.5) < 1e-6
        xi3_mn = buf.get_instance('i3/mn')
        assert xi3_mn.get_param('w').value == 'w'
        assert xi3_mn.eval_ref_param('w') == 5.0
        assert xi3_mn.eval_ref_param('l') == 1.0
        assert abs(xi3_mn.eval_ref_param('cg') - 0.25) < 1e-6

class TestL3HierarchicalParams:
    def make_ckt(self):
        f = StringIO(dedent(
            """\
            .macromodel pch_mac pmos d g s b m=1
            +cga='1fF/(1um * 20nm)'
            +cg="m * w * l * cga"
            .macromodel nch_mac nmos d g s b m=1
            +cga='1fF/(1um * 20nm)'
            +cg="m * w * l * cga"

            .subckt pinv a y vdd vss w=2 l=2.0
            xmp y a vdd vdd pch_mac w="2*W" l=1.0
            xmn y a vss vss nch_mac W=w     l=1.0
            .ends

            .subckt buf a y vdd vss w1=0 w2=3 w3=5
            xi1 a n vdd vss pinv
            xi2 n y vdd vss pinv w='(w2)'
            xi3 n y vdd vss pinv w=w3 l=5
            .ends
            """))
        f.name = "<string>"
        ckt = Ckt()
        ckt.read_spice(f)
        return ckt

    def test_hier_flatten_param_eval(self):
        ckt = self.make_ckt()
        buf = ckt.get_cell('buf')
        buf.link()
        buf.ungroup(flatten=True)

        xi1_mp = buf.get_instance('i1/mp')
        assert xi1_mp.get_param('w').value == '2*w'
        assert xi1_mp.eval_ref_param('w') == 4.0
        assert xi1_mp.eval_ref_param('l') == 1.0
        assert xi1_mp.eval_ref_param('cg') == 0.2
        xi1_mn = buf.get_instance('i1/mn')
        assert xi1_mn.get_param('w').value == 'w'
        assert xi1_mn.eval_ref_param('w') == 2.0
        assert xi1_mn.eval_ref_param('l') == 1.0
        assert xi1_mn.eval_ref_param('cg') == 0.1

        xi2_mp = buf.get_instance('i2/mp')
        assert xi2_mp.get_param('w').value == '2*w'
        assert xi2_mp.eval_ref_param('w') == 6.0
        assert xi2_mp.eval_ref_param('l') == 1.0
        assert abs(xi2_mp.eval_ref_param('cg') - 0.3) < 1e-6
        xi2_mn = buf.get_instance('i2/mn')
        assert xi2_mn.get_param('w').value == 'w'
        assert xi2_mn.eval_ref_param('w') == 3.0
        assert xi2_mn.eval_ref_param('l') == 1.0
        assert abs(xi2_mn.eval_ref_param('cg') - 0.15) < 1e-6

        xi3_mp = buf.get_instance('i3/mp')
        assert xi3_mp.get_param('w').value == '2*w'
        assert xi3_mp.eval_ref_param('w') == 10.0
        assert xi3_mp.eval_ref_param('l') == 1.0
        assert abs(xi3_mp.eval_ref_param('cg') - 0.5) < 1e-6
        xi3_mn = buf.get_instance('i3/mn')
        assert xi3_mn.get_param('w').value == 'w'
        assert xi3_mn.eval_ref_param('w') == 5.0
        assert xi3_mn.eval_ref_param('l') == 1.0
        assert abs(xi3_mn.eval_ref_param('cg') - 0.25) < 1e-6

class TestL4HierarchicalParams:
    def make_ckt(self):
        f = StringIO(dedent(
            """\
            .macromodel pch_mac pmos d g s b m=1
            +cga='1fF/(1um * 20nm)'
            +cg="m * w * l * cga"
            .macromodel nch_mac nmos d g s b m=1
            +cga='1fF/(1um * 20nm)'
            +cg="m * w * l * cga"

            .subckt pinv a y vdd vss wp=1 wn=1
            xmp y a vdd vdd pch_mac w=wp l=1
            xmn y a vss vss nch_mac W=wn l=1
            .ends

            .subckt inv a y vdd vss wp=1 wn=1
            xi0 a y vdd vss pinv wp=wp wn=wn
            .ends

            .subckt buf a y vdd vss wp=2 wn=2
            xi0 a n vdd vss inv wp=wp wn=wn
            xi1 n y vdd vss inv wp="2*wp" wn="2*wn"
            .ends
            """))
        f.name = "<string>"
        ckt = Ckt()
        ckt.read_spice(f)
        return ckt

    def test_hier_flatten_param_eval(self):
        ckt = self.make_ckt()
        ckt.link()
        buf = ckt.get_cell('buf')
        buf.ungroup(flatten=True)

        i0_i0_mp = buf.get_instance('i0/i0/mp')
        assert i0_i0_mp.eval_ref_param('w') == 2.0

        i1_i0_mp = buf.get_instance('i1/i0/mp')
        assert i1_i0_mp.eval_ref_param('w') == 4.0
