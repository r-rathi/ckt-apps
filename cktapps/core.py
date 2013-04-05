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
    def __init__(self, name):
        self.name = name
    def __repr__(self):
        return "Port(%s)" % self.name

class Net(object):
    def __init__(self, name):
        self.name = name
    def __repr__(self):
        return "Net(%s)" % self.name

class Instance(object):
    def __init__(self, name, refname, params):
        self.name = name

        self.refname = refname
        self.ref = None
        self.owner = None

        self.pins = []

        if params is None:
            self.params = {}
        else:
            self.params = params

        self.is_hierarchical = False
        self.is_linked = False

        self._eval_params = None

    #def full_name(self):
    #    scope_path = "/".join([cell.name for cell in self.scope_path])
    #    return scope_path + "/" + self.name

    #---------------------------------------------------------------------------
    def add_pins_by_pos(self, *netnames): pass
    def add_pins_by_name(self, **portmap): pass
    def add_pin(self, name, net):
        port = Port(name)
        pin = Pin(port, self, net)
        self.pins.append(pin)

    def add_pinobj(self, pin):
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
    def get_param(self, param):
        return self.params[param]

    def _tostr(self, s):
        if isinstance(s, basestring):
            return s
        else:
            return str(s)

    def _destr(self, s):
        if isinstance(s, basestring) and re.search('"', s):
            #print('removing ":', s)
            s = re.sub('"', '', s)
        else:
            #print('converting to float', s)
            s = float(s)
        #print('>>', s)
        return s

    def eval_param(self, param):
        if self._eval_params is None:
            # initialize _eval_params with refcell params
            self._eval_params = {}
            prim = self.owner.search_scope_prim(self.refname)
            for k, v in prim.params.items():
                v = self._destr(v.lower())
                self._eval_params[k.lower()] = v

            # eval instance (self) params in parent_cell namespace and
            # add/overwrite to _eval_params
            parent_cell_ns = {}
            for k, v in self.owner.params.items():
                parent_cell_ns[k.lower()] = float(v)

            #print("pns:", self, self.container, self.container.owner.name, parent_cell_ns)
            for k, v in self.params.items():
                v = self._destr(v.lower())
                if isinstance(v, basestring):
                    v = eval(v, {"__builtins__":None}, parent_cell_ns)
                self._eval_params[k.lower()] = v

        p = self._eval_params[param.lower()]
        p = re.sub('"', '', p)
        if isinstance(p, basestring):
            #print("Will eval %s with vars %s" % (p, self._eval_params))
            p = eval(p, {"__builtins__":None}, self._eval_params)
            #print(">>", p)
        return p

    #---------------------------------------------------------------------------
    def link(self):
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
    def ungroup(self, flatten=False):
        if not self.is_hierarchical: return
        #print("ungrouping %r" % self)

        if not self.is_linked:
            raise(LinkError("can't ungroup %r before it's linked" % self))
        assert self.ref is not None

        if flatten:
            #TODO: maybe we should copy ref before ungroup(flatten=True)
            self.ref.ungroup(flatten=True)

        port2net_map = {}
        for pin in self.all_pins():
            port2net_map[pin.port.name] = pin.net.name

        netname_map = {}
        for net in self.ref.all_nets():
            old_netname = net.name
            if old_netname in port2net_map:
                new_netname = port2net_map[old_netname]
            else:
                new_netname = self.name + "/" + old_netname
            netname_map[old_netname] = new_netname
            self.owner.add_net(new_netname)
            #print("adding", new_netname)

        #print("netname_map:", netname_map)

        for old_inst in self.ref.all_instances():
            new_inst = copy.copy(old_inst)
            new_inst.name = self.name + "/" + new_inst.name
            new_inst.pins = [] #FIXME: api
            #print("\nadding", new_inst)
            #self.add_instance(new_inst)
            #self.instances[new_inst.name.lower()] = new_inst #FIXME: api
            self.owner.add_instance_obj(new_inst)
            for pin in old_inst.all_pins():
                #print("\nprocessing pin:", pin)
                new_port = pin.port #copy.copy(pin.port)
                #print("looking up:", pin.net.name, "=>", netname_map[pin.net.name])
                new_net  = self.owner.get_net(netname_map[pin.net.name])
                new_pin  = Pin(new_port, new_inst, new_net)
                new_inst.add_pinobj(new_pin)
                #print("adding new pin:", new_pin)

        self.owner.del_instance(self.name)

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

class Parameter(object):
    def __init__(self, name, value, namespace):
        self.name = name
        self._value = value
        self._namespace = namespace

    def eval():
        pass

    def value():
        pass

class Cell(object):
    """ Cell is the fundamental container of all the circuit elements. A
    hierachical design is divided into multiple Cells. Cell maps to .subckt
    in spice and module in verilog.
    
    A cell also acts as a declaration scope, allowing nested cell defintions.
    """
    def __init__(self, name, params=None):
        self.name = name

        if params is None:
            self.params = collections.OrderedDict()
        else:
            self.params = params

        self.cells = collections.OrderedDict()
        self.prims = collections.OrderedDict()
        self.ports = collections.OrderedDict()
        self.nets = collections.OrderedDict()
        self.instances = collections.OrderedDict()

        self.owner = None
        self._ref_count = 0

    def full_name(self):
        scope = self
        scope_path = collections.deque()
        while scope:
            scope_path.appendleft(scope.name)
            scope = scope.owner
        return "/".join(scope_path)

    #def add(self, objtype, obj):
    #    self.objects[objtype][obj.name.lower()] = obj

    #def find(self, objtype, objname=None):
    #    if objname:
    #        return 

    #---------------------------------------------------------------------------
    def add_cell(self, name, *args, **kwargs):
        if name is None:
            raise CktObjValueError("cell has no name")
        cell = Cell(name, *args, **kwargs)
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
    def add_prim(self, name, *args, **kwargs):
        if name is None:
            raise CktObjValueError("prim has no name")
        prim = Prim(name, *args, **kwargs)
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
        net = Net(name, *args, **kwargs)
        net.owner = self
        self.nets[name] = net
        return net

    def all_nets(self):
        return self.nets.itervalues()

    def get_net(self, name):
        try:
            return self.nets[name]
        except KeyError:
            raise CktObjDoesNotExist("'%s' in: '%s'" % (name, self))

    #---------------------------------------------------------------------------
    def add_port(self, name, *args, **kwargs):
        if name is None:
            raise CktObjValueError("port has no name")
        port = Port(name, *args, **kwargs)
        port.owner = self
        self.ports[name] = port
        return port

    def all_ports(self):
        return self.ports.itervalues()

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
        for cell in self.all_cells():
            cell.link()
        for inst in self.all_instances():
            inst.link()

    #---------------------------------------------------------------------------
    def ungroup(self, instname=None, flatten=False):
        #print("ungrouping %r" % self)
        if instname:
            inst = self.get_instance(instname)
            inst.ungroup(flatten)
        else:
            # not using self.all_instances() here becase ungroup modifies the
            # self.instances dict
            for inst in list(self.all_instances()):
                inst.ungroup(flatten)

    #---------------------------------------------------------------------------
    def __repr__(self):
        return "Cell(%s)" % self.name

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
    def __init__(self, name, type, portnames, params=None):
        super(Prim, self).__init__(name, params)
        self.type = type
        self.portnames = portnames

#-------------------------------------------------------------------------------
class Ckt(Cell):
    """ Ckt class represents the top-level of the design. Ckt is essentially a
    Cell that acts as the root declaration scope. This maps to the top-level in
    spice format or $root in verilog.
    """

    def __init__(self, name="$root", params=None):
        super(Ckt, self).__init__(name, params)
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
