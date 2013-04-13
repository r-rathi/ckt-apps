""" cktapps core circuit netlist-database classes

The circuit netlist database represents the basic circuit elements and their
connectivity. The database supports hierarchical designs, and can be queried
as well as modified through the core API interface.
"""

#-------------------------------------------------------------------------------
from __future__ import absolute_import
from __future__ import print_function
import collections, copy, re

from cktapps.formats import spice

#-------------------------------------------------------------------------------
class InternalError(Exception): pass
class LinkError(Exception): pass
class FileFormatError(Exception): pass
class CktObjTypeError(Exception): pass
class CktObjValueError(Exception): pass
class CktObjDoesNotExist(Exception): pass

#-------------------------------------------------------------------------------
class CktObj(object):
    """ Base circuit object """

    def __init__(self, name):
        self.name = name
        self.container = None

    def copy(self, name):
        pass

    def __repr__(self):
        return "<%s(name=%s) id=%s>" % (self.__class__.__name__, self.name,
                                        hex(id(self)))


class CktObjContainer(object):
    """ Object container indexed with name """

    def __init__(self, objtype, owner):
        self.objtype = objtype
        self.objects = collections.OrderedDict()
        self.owner = owner

    def add(self, name, *args, **kwargs):
        obj = self.objtype(name, *args, **kwargs)
        obj.container = self
        self.objects[name] = obj
        return obj

    def addobj(self, obj):
        if not isinstance(obj, self.objtype):
            raise CktObjTypeError("can't add '%r' to '%r'" % (obj, self))
        if obj.name is None:
            raise CktObjValueError("obj '%r' has no name" % obj)
        obj.container = self
        self.objects[obj.name] = obj
        return obj

    def all(self):
        return self.objects.itervalues()

    def get(self, name):
        try:
            return self.objects[name]
        except KeyError:
            raise CktObjDoesNotExist("'%s' in: '%s'" % (name, self))

    def get_default(self, name, default=None):
        return self.objects.get(name, default)

    def delete(self, name):
        del self.objects[name]

    def filter(self, name):
        re_name = re.compile(r'^%s$' % name)
        return (obj for obj in self.all() if re_name.match(obj.name))

    def as_list(self):
        pass
    def as_dict(self):
        pass
    def as_set(self):
        pass

    def __repr__(self):
        return "<%s(type=%s)>" % (self.__class__.__name__,
                                  self.objtype.__name__)

class CktObjList(object):
    def __init__(self, objtype, owner):
        self.objtype = objtype
        self.objects = []
        self.owner = owner

    def add(self, *args, **kwargs):
        obj = self.objtype(*args, **kwargs)
        obj.container = self
        self.objects.append(obj)
        return obj

    def addobj(self, obj):
        if not isinstance(obj, self.objtype):
            raise CktObjTypeError("can't add '%r' to '%r'" % (obj, self))
        obj.container = self
        self.objects.append(obj)
        return obj

    def all(self):
        return self.objects

    def get(self, name):
        for obj in self.objects:
            if obj.name == name:
                return obj
        raise CktObjDoesNotExist("'%s' in: '%s'" % (name, self))

    def get_default(self, name, default=None):
        for obj in self.objects:
            if obj.name == name:
                return obj
        return default

    def index(self, name):
        for i, obj in enumerate(self.objects):
            if obj.name == name:
                return i
        raise CktObjDoesNotExist("'%s' in: '%s'" % (name, self))

    def delete(self, name):
        i = self.index(name)
        self.objects.pop(i)

    def filter(self, name):
        re_name = re.compile(r'^%s$' % name)
        return (obj for obj in self.objects if re_name.match(obj.name))

    def __repr__(self):
        return "<%s(type=%s)>" % (self.__class__.__name__,
                                  self.objtype.__name__)

class PinContainer(CktObjList):
    def __init__(self, owner):
        super(PinContainer, self).__init__(Pin, owner)

    def add(self, name, net):
        port = Port(name)
        pin = Pin(port, self.owner, net)
        pin.container = self
        self.objects.append(pin)
        return pin

    def addobj(self, obj):
        if not isinstance(obj, self.objtype):
            raise CktObjTypeError("can't add '%r' to '%r'" % (obj, self))
        obj.container = self
        self.objects.append(obj)
        return obj

#-------------------------------------------------------------------------------
class Port(object):
    def __init__(self, name, owner):
        self.name = name
        self.owner = owner
    def __repr__(self):
        return "Port(%s)" % self.name

class Net(object):
    def __init__(self, name, owner):
        self.name = name
        self.owner = owner
    def __repr__(self):
        return "Net(%s)" % self.name

class Param(object):
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def eval(self, namespace):
        return eval(self.value, {"__builtins__":None}, namespace)

    def __repr__(self):
        return "Param(%s, %s)" % (self.name, self.value)

class Instance(object):
    def __init__(self, name, refname, params):
        self.name = name

        self.refname = refname
        self.ref = None
        self.owner = None

        self.pins = []

        self.params = collections.OrderedDict()

        for name, value in params.items():
            param = Param(name, value)
            self.params[name] = param

        self._ctx = None
        #self._owner_ctx = None
        self._ref_ctx = None

        self.is_hierarchical = False
        self.is_linked = False

        self._eval_params = None

    #def full_name(self):
    #    scope_path = "/".join([cell.name for cell in self.scope_path])
    #    return scope_path + "/" + self.name

    #---------------------------------------------------------------------------
    def _uniq(self, name, ctx):
        # unique (de-contextualized) copy
        cpy = copy.copy(self)
        cpy.name = name
        if not cpy._ctx:
            cpy._ctx = cpy._build_ctx(ctx)
        if not cpy._ref_ctx:
            cpy._ref_ctx = cpy.ref._build_ctx(cpy._ctx)
        return cpy

    #---------------------------------------------------------------------------
    def add_pins_by_pos(self, *netnames): pass
    def add_pins_by_name(self, **portmap): pass
    def add_pin(self, name, net):
        port = Port(name, owner=None)
        pin = Pin(port=port, instance=self, net=net)
        self.pins.append(pin)
        return pin

    def add_pin_obj(self, pin):
        if not isinstance(pin, Pin):
            raise CktObjTypeError("can't add '%r' to '%r'" % (pin, self))
        pin.instance = self
        self.pins.append(pin)
        return pin

    def all_pins(self):
        return iter(self.pins)

    def get_pin(self, name):
        for pin in self.pins:
            if pin.name == name:
                return pin
        raise CktObjDoesNotExist("'%s' in: '%s'" % (name, self))

    #---------------------------------------------------------------------------
    def add_param(self, name, value):
        if name is None:
            raise CktObjValueError("param has no name")
        param = Param(name, value)
        self.params[name] = param
        return param

    def all_params(self):
        return self.params.itervalues()

    def get_param(self, name):
        try:
            return self.params[name]
        except KeyError:
            raise CktObjDoesNotExist("'%s' in: '%s'" % (name, self))

    def eval_param(self, name, ctx=None):
        assert self.owner is not None
        if ctx is None:
            cell_ctx = self.owner._build_ctx({})
        else:
            cell_ctx = ctx

        if self._ctx is None:
            inst_ctx = self._build_ctx(cell_ctx)
        else:
            inst_ctx = self._ctx

        try:
            return inst_ctx[name]
        except KeyError:
            raise CktObjDoesNotExist("'%s' in: '%s'" % (name, self))

    def eval_ref_param(self, name, ctx=None):
        if not self.is_linked:
            raise(LinkError("can't eval ref param '%s' "
                            "(%r not linked yet)" % (name, self)))
        if self._ctx is None:
            if ctx is None:
                assert self.owner is not None
                cell_ctx = self.owner._build_ctx({})
            else:
                cell_ctx = ctx
            inst_ctx = self._build_ctx(cell_ctx)
        else:
            inst_ctx = self._ctx

        if self._ref_ctx is None:
            assert self.ref is not None
            ref_ctx = self.ref._build_ctx(inst_ctx)
        else:
            ref_ctx = self._ref_ctx

        try:
            return ref_ctx[name]
        except KeyError:
            raise CktObjDoesNotExist("'%s' in: '%s'" % (name, self))


    def _build_ctx(self, ctx):
        #print("> cell ctx:", self, ctx)
        # evaluate only inst params (in cell context)
        inst_ctx = {}
        for pname, p in self.params.items():
            inst_ctx[pname] = p.eval(ctx)
        #print("< inst ctx:", self, inst_ctx)
        return inst_ctx

    #---------------------------------------------------------------------------
    def link(self):
        #print("Linking:", self)
        if self.is_linked: return
        self._resolve_ref()
        self._bind()
        self.is_linked = True

    def _resolve_ref(self):
        if self.ref: return

        #print("Resolving ref... inst: %s/%s" %
              #(self.owner.full_name(), self.name), end=' ')
        try:
            ref = self.owner.search_scope_prim(self.refname)
        except CktObjDoesNotExist:
            try:
                ref = self.owner.search_scope_cell(self.refname)
            except:
                raise LinkError(
                    "failed to resolve ref '%s' of '%s' in cell '%s'" %
                    (self.refname, self.name, self.owner.full_name()))
        #print("=> cell/prim:", ref.full_name())

        ref._ref_count += 1
        self.ref = ref


    def _bind(self):
        assert self.ref is not None

        inst_pins = self.pins
        ref_ports = self.ref.ports.values()

        if len(inst_pins) != len(ref_ports):
            raise LinkError("port count mismatch\n"
                            "> cell %s : %s\n"
                            "> inst %s : %s" %
                            (self.ref.full_name(),
                             [port.name for port in ref_ports],
                             self.ref.full_name() + "/" + self.name,
                             [pin.net.name for pin in inst_pins]))

        for pin, port in zip(inst_pins, ref_ports):
                pin.port = port


    #---------------------------------------------------------------------------
    def ungroup(self, owner, flatten=False, prefix='', sep='/', ctx=None):
        #print("ungrouping %r:" % self, ctx)
        if not self.is_hierarchical:
            #print("--> not hierarchical")
            return

        if not self.is_linked:
            raise(LinkError("can't ungroup %r before it's linked" % self))
        assert self.ref is not None

        # build inst context
        if ctx is None:
            inst_ctx = self._build_ctx({})
        else:
            inst_ctx = self._build_ctx(ctx)

        if flatten:
            uniq_ref = self.ref._uniq()
            ref_ctx  = uniq_ref.ungroup(flatten=True, prefix='', sep=sep,
                                        ctx=inst_ctx)
        else:
            uniq_ref = self.ref
            ref_ctx = uniq_ref._build_ctx(inst_ctx)

        presep = prefix + self.name + sep

        pinmap = {}
        for pin in self.all_pins():
            pinmap[pin.port.name] = pin

        for inst in list(uniq_ref.all_instances()):
            uniq_inst = inst._uniq(name=presep + inst.name, ctx=ref_ctx)
            #self.owner.add_instance_obj(uniq_inst)
            owner.add_instance_obj(uniq_inst)
            uniq_inst.pins = []
            for pin in inst.all_pins():
                if pin.net.name in pinmap:
                    net = pinmap[pin.net.name].net
                else:
                    #net = self.owner.get_net_else_add(presep + pin.net.name)
                    net = owner.get_net_else_add(presep + pin.net.name)
                uniq_inst.add_pin_obj(Pin(pin.port, uniq_inst, net))

        #self.owner.del_instance(self.name)
        owner.del_instance(self.name)

    #---------------------------------------------------------------------------
    def __repr__(self):
        if self.is_linked and self.ref:
            refname = self.ref.full_name()
        else:
            refname = self.refname
        return "Instance(%s, %s)" % (self.name, refname)

class Pin(object):
    def __init__(self, port, instance, net):
        self.port = port
        self.instance = instance
        self.net = net

    def __repr__(self):
        return "Pin(%r, %r, %r)" % (self.port, self.instance, self.net)

class Cell(object):
    """ Cell is the fundamental container of all the circuit elements. A
    hierachical design is divided into multiple Cells. Cell maps to .subckt
    in spice and module in verilog.
    
    A cell also acts as a declaration scope, allowing nested cell defintions.
    """
    def __init__(self, name, portnames, params):
        self.name = name

        self.owner = None

        self.cells = collections.OrderedDict()
        self.prims = collections.OrderedDict()
        self.ports = collections.OrderedDict()
        self.nets = collections.OrderedDict()
        self.instances = collections.OrderedDict()
        self.params = collections.OrderedDict()

        for name in portnames:
            net = Net(name, owner=self)
            self.nets[name] = net
            port = Port(name, owner=self)
            self.ports[name] = port

        for name, value in params.items():
            param = Param(name, value)
            self.params[name] = param

        #self._ctx = None
        self._ref_count = 0

    def full_name(self):
        scope = self
        scope_path = collections.deque()
        while scope:
            scope_path.appendleft(scope.name)
            scope = scope.owner
        return "/".join(scope_path)

    #---------------------------------------------------------------------------
    def _uniq(self):
        cpy = copy.copy(self)
        cpy.instances = collections.OrderedDict(self.instances)
        return cpy

    #---------------------------------------------------------------------------
    def add_cell(self, name, portnames, params=None):
        if name is None:
            raise CktObjValueError("cell has no name")
        cell = Cell(name, portnames, params)
        cell.owner = self
        self.cells[name] = cell
        return cell

    def all_cells(self):
        return self.cells.itervalues()

    def get_cell(self, name):
        try:
            return self.cells[name]
        except KeyError:
            raise CktObjDoesNotExist("'%s' in: '%s'" % (name, self))

    #---------------------------------------------------------------------------
    def add_prim(self, name, type, portnames, params=None):
        if name is None:
            raise CktObjValueError("prim has no name")
        prim = Prim(name, type, portnames, params)
        prim.owner = self
        self.prims[name] = prim
        return prim

    def all_prims(self):
        return self.prims.itervalues()

    def get_prim(self, name):
        try:
            return self.prims[name]
        except KeyError:
            raise CktObjDoesNotExist("'%s' in: '%s'" % (name, self))

    #---------------------------------------------------------------------------
    def add_instance(self, name, *args, **kwargs):
        if name is None:
            raise CktObjValueError("instance has no name")
        instance = Instance(name, *args, **kwargs)
        instance.owner = self
        self.instances[name] = instance
        return instance

    def add_instance_obj(self, instance):
        if not isinstance(instance, Instance):
            raise CktObjTypeError("can't add '%r' to '%r'" % (instance, self))
        if instance.name is None:
            raise CktObjValueError("instance '%r' has no name" % instance)
        instance.owner = self
        self.instances[instance.name] = instance
        return instance

    def all_instances(self):
        return self.instances.itervalues()

    def get_instance(self, name):
        try:
            return self.instances[name]
        except KeyError:
            raise CktObjDoesNotExist("'%s' in: '%s'" % (name, self))

    def del_instance(self, name):
        del self.instances[name]

    #---------------------------------------------------------------------------
    def add_net(self, name, *args, **kwargs):
        if name is None:
            raise CktObjValueError("net has no name")
        net = Net(name, owner=self)
        self.nets[name] = net
        return net

    def all_nets(self):
        return self.nets.itervalues()

    def get_net(self, name): #, autocreate=False):
        try:
            return self.nets[name]
        except KeyError:
            #if autocreate:
            #    self.add_net(name)
            #else:
            raise CktObjDoesNotExist("'%s' in: '%s'" % (name, self))

    def get_net_else_add(self, name):
        return self.nets.setdefault(name, Net(name, owner=self))

    #---------------------------------------------------------------------------
    def add_port(self, name):
        if name is None:
            raise CktObjValueError("port has no name")
        port = Port(name, owner=self)
        self.ports[name] = port
        return port

    def all_ports(self):
        return self.ports.itervalues()

    #---------------------------------------------------------------------------
    def add_param(self, name, value):
        if name is None:
            raise CktObjValueError("param has no name")
        param = Param(name, value)
        self.params[name] = param
        return param

    def all_params(self):
        return self.params.itervalues()

    def get_param(self, name):
        try:
            return self.params[name]
        except KeyError:
            raise CktObjDoesNotExist("'%s' in: '%s'" % (name, self))

    def eval_param(self, name, ctx=None):
        if ctx is None:
            inst_ctx = {}
        else:
            inst_ctx = ctx

        cell_ctx = self._build_ctx(inst_ctx)

        try:
            return cell_ctx[name]
        except KeyError:
            raise CktObjDoesNotExist("'%s' in: '%s'" % (name, self))

    def _build_ctx(self, ctx):
        #print("> inst ctx:", self, ctx)
        # parameters found in inst context override cell params
        cell_ctx = dict(ctx)
        for pname, p in self.params.items():
            cell_ctx.setdefault(pname, p.eval(cell_ctx))
        #print("< cell ctx:", self, cell_ctx)
        return cell_ctx

    #---------------------------------------------------------------------------
    def search_scope_cell(self, name):
        scope = self
        while scope:
            cell = scope.cells.get(name)
            if cell: return cell
            scope = scope.owner
        raise CktObjDoesNotExist(name)

    def search_scope_prim(self, name):
        scope = self
        while scope:
            prim = scope.prims.get(name)
            if prim: return prim
            scope = scope.owner
        raise CktObjDoesNotExist(name)

    #---------------------------------------------------------------------------
    def link(self):
        #print("Linking:", self)
        for cell in self.all_cells():
            cell.link()
        for inst in self.all_instances():
            inst.link()

    #---------------------------------------------------------------------------
    def ungroup(self, instname=None, flatten=False, prefix='', sep='/',
                ctx=None):
        #print("ungrouping %r:" % self)
        if ctx is None:
            cell_ctx = self._build_ctx({})
        else:
            cell_ctx = self._build_ctx(ctx)

        if instname:
            inst = self.get_instance(instname)
            inst.ungroup(owner=self, flatten=flatten, prefix=prefix, sep=sep,
                         ctx=cell_ctx)
        else:
            # need to make a copy using list() becase inst.ungroup() modifies
            # the self.instances dict
            for inst in list(self.all_instances()):
                inst.ungroup(owner=self, flatten=flatten, prefix=prefix,
                             sep=sep, ctx=cell_ctx)
        return cell_ctx

    #---------------------------------------------------------------------------
    def __repr__(self):
        return "Cell(%s)" % self.full_name()

    #def __repr__(self):
    #    lev = len(self.scope_path)
    #    indent = " " * 4

    #    r  = "%s(%s) {\n" % (self.__class__.__name__, self.full_name())
    #    for port in self.ports.values():
    #        r += indent*(lev+1) + str(port) + "\n"
    #    r += indent*(lev+1) + "Params(" + str(self.params) + ")\n"
    #    for net in self.nets.values():
    #        r += indent*(lev+1) + str(net) + "\n"
    #    for instance in self.instances.values():
    #        r += indent*(lev+1) + str(instance) + "\n"
    #    for pin in self.find_pin():
    #        r += indent*(lev+1) + str(pin) + "\n"
    #    for cell in self.cells.values():
    #        r += indent*(lev+1) + str(cell) + "\n"
    #    r += indent*lev + "}"
    #    return r

#-------------------------------------------------------------------------------
class Prim(Cell):
    def __init__(self, name, type, portnames, params):
        super(Prim, self).__init__(name, portnames, params)
        self.type = type
        self.portnames = portnames

#-------------------------------------------------------------------------------
class Ckt(Cell):
    """ Ckt class represents the top-level of the design. Ckt is essentially a
    Cell that acts as the root declaration scope. This maps to the top-level in
    spice format or $root in verilog.
    """

    def __init__(self, name="", params=None):
        if params is None:
            params = {}
        super(Ckt, self).__init__(name, portnames=[], params=params)
        self._reader_cache = {}

    def get_topcells(self):
        top_cells = []
        for cell in self.all_cells():
            if cell._ref_count == 0:
                top_cells.append(cell)
        #print("Top cells: %s" % top_cells)
        return top_cells


    def read_spice(self, f):
        """ Read a spice file into the Ckt database

        - f : file or filetype object
        """
        spice.Reader(self).read(f)

    def write_spice(self, cell, f=None):
        """ Write a cell to a file in the spice format

        - cell : cell to write
        - f    : file or filetype object
        """
        spice.Writer(cell).write()

#-------------------------------------------------------------------------------
