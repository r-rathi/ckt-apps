""" cktapps core circuit netlist-database classes

The circuit netlist database represents the basic circuit elements and their
connectivity. The database supports hierarchical designs, and can be queried
as well as modified through the core API interface.
"""

#-------------------------------------------------------------------------------
from __future__ import absolute_import
from __future__ import print_function
import collections, copy, re

import importlib # Python 2.7 only?

from cktapps.formats import spice

#-------------------------------------------------------------------------------
class InternalError(Exception): pass
class LinkingError(Exception): pass
class FileFormatError(Exception): pass

#-------------------------------------------------------------------------------
class Port(object):
    def __init__(self, name):
        self.name = name
    
    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, self.name)

class Net(object):
    def __init__(self, name):
        self.name = name
    
    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, self.name)

class Instance(object):
    def __init__(self, name, cellname, params):
        self.name = name
        self.cellname = cellname
        self.cell = None
        self.ishier = False
        self.pins = []
        self.parent_cell = None

        if params is None:
            self.params = {}
        else:
            self.params = params

        self._eval_params = None

    #def full_name(self):
    #    scope_path = "/".join([cell.name for cell in self.scope_path])
    #    return scope_path + "/" + self.name

    def add_pinobj(self, pin):
        self.pins.append(pin)

    def add_pin(self, name, net):
        port = Port(name)
        pin = Pin(port, self, net)
        self.pins.append(pin)

    def find_pin(self, pinname=None):
        if pinname:
            return [pin for pin in self.pins if pin.port.name == pinname]
        else:
            return self.pins

    def get_param(self, param):
        return self.params[param]

    def _tostr(self, s):
        if isinstance(s, basestring):
            return s
        else:
            return str(s)

    def _destr(self, s):
        if re.search('"', s):
            return re.sub('"', '', s)
        else:
            return float(s)

    def eval_param(self, param, namespace=None):
        if namespace is None:
            namespace = self.parent_cell.params

        if self._eval_params is None:
            prim = self.parent_cell.search_scope_prim(self.cellname)
            self._eval_params = prim.params.copy()
            self._eval_params.update(self.params)

        pstr = self._eval_params[param]
        pstr = pstr.lower()
        pstr = re.sub('"', '', pstr)

        ns = {}
        for k, v in self._eval_params.items():
            ns[k.lower()] = self._destr(v.lower())

        #print("Will eval %s with vars %s" % (pstr, ns)) # self._eval_params))
        pval = eval(pstr, {"__builtins__":None}, ns) #self._eval_params)
        return pval

    def bind(self, cell):
        cell_portnames = [port.name for port in cell.find_port()]

        if (len(cell_portnames) == len(self.pins)):
            for pin, portname in zip(self.pins, cell_portnames):
                pin.port.name = portname
        else:
            raise LinkingError("port count mismatch\ncell %s : %s\ninst %s : %s" %
                               (cell.full_name(), cell_portnames,
                                self.full_name() + "/" + inst.name,
                                [pin.net.name for pin in inst_pins]))

        for param in inst.params.keys():
            if param == "m":
                continue
            try:
                p = cell.params[param]
            except KeyError:
                msg = "extra parameter '%s' in instance '%s' of '%s'"
                raise LinkingError(msg % (param,
                                          self.full_name() + "/" + inst.name,
                                          cell.full_name() ))

        inst.cell = cell


    def __repr__(self):
        if self.cell:
            ref_cellname = self.cell.full_name()
        else:
            ref_cellname = "<unresolved>"
        return "%s(%s, %s => %s)" % (self.__class__.__name__, self.name, \
                                     self.cellname, ref_cellname)

class Pin(object):
    def __init__(self, port, instance, net):
        self.port = port
        self.instance = instance
        self.net = net

    def __repr__(self):
        return "%s(%r, %r, %r)" % (self.__class__.__name__, \
                                   self.port, self.instance, self.net)
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

        #self.objects = {}
        #self.objects['port']     = collections.OrderedDict()
        #self.objects['net']      = collections.OrderedDict()
        #self.objects['instance'] = collections.OrderedDict()
        #self.objects['cell']     = collections.OrderedDict()
        #self.objects['pin']      = []
        self.ports = collections.OrderedDict()
        self.nets = collections.OrderedDict()
        self.instances = collections.OrderedDict()
        self.cells = collections.OrderedDict()
        self.prims = collections.OrderedDict()
        #self.pins = []
        self.scope_path = []

    def full_name(self):
        scope_path = "/".join([cell.name for cell in self.scope_path])
        return scope_path + "/" + self.name

    #def add(self, objtype, obj):
    #    self.objects[objtype][obj.name.lower()] = obj

    #def find(self, objtype, objname=None):
    #    if objname:
    #        return 

    def add_port(self, name):
        port = Port(name)
        self.ports[name.lower()] = port
        return port

    def add_net(self, name):
        net = Net(name)
        self.nets[name.lower()] = net
        return net

    def add_instance(self, name, refcellname, params): 
        instance = Instance(name, refcellname, params)
        instance.parent_cell = self
        self.instances[name.lower()] = instance
        return instance

    def add_cell(self, name, params):
        cell = Cell(name, params)
        self.cells[name.lower()] = cell
        return cell

    def add_prim(self, name, type, portnames, params):
        prim = Prim(name, type, portnames, params)
        self.prims[name.lower()] = prim
        return prim

    def find_port(self, name=None):
        if name:
            return self.ports[name.lower()]
        else:
            return self.ports.values()

    def find_net(self, name=None):
        if name:
            return self.nets[name.lower()]
        else:
            return self.nets.values()

    def find_instance(self, name=None):
        if name:
            return self.instances[name.lower()]
        else:
            return self.instances.values()

    def find_cell(self, name=None):
        if name:
            return self.cells[name.lower()]
        else:
            return self.cells.values()

    def find_prim(self, name=None):
        if name:
            return self.prims[name.lower()]
        else:
            return self.prims.values()

    def find_pin(self, instname=None, pinname=None):
        if instname:
            return self.find_instance(instname).find_pin(pinname)
        else:
            pins = []
            for inst in self.find_instance():
                pins += inst.find_pin(pinname)
            return pins

    def bind_inst2cell(self, inst, cell):
        cell_portnames = [port.name for port in cell.find_port()]
        inst_pins = [pin for pin in self.find_pin() if pin.instance == inst]

        if (len(cell_portnames) == len(inst_pins)):
            for pin, portname in zip(inst_pins, cell_portnames):
                pin.port.name = portname
        else:
            raise LinkingError("port count mismatch\ncell %s : %s\ninst %s : %s" %
                               (cell.full_name(), cell_portnames,
                                self.full_name() + "/" + inst.name,
                                [pin.net.name for pin in inst_pins]))

        for param in inst.params.keys():
            if param == "m":
                continue
            try:
                p = cell.params[param]
            except KeyError:
                msg = "extra parameter '%s' in instance '%s' of '%s'"
                raise LinkingError(msg % (param,
                                          self.full_name() + "/" + inst.name,
                                          cell.full_name() ))

        inst.cell = cell


    def flatten_instance(self, inst):
        inst_netnames = [pin.net.name for pin in inst.find_pin()]
        #TODO: check whether refs resolved or not
        cell_portnames = [port.name for port in inst.cell.find_port()]
        port2net_map = {}
        for portname, netname in zip(cell_portnames, inst_netnames):
            port2net_map[portname] = netname

        netname_map = {}
        for net in inst.cell.find_net():
            old_netname = net.name
            if old_netname in port2net_map:
                new_netname = port2net_map[old_netname]
            else:
                new_netname = inst.name + "/" + old_netname
            netname_map[old_netname] = new_netname
            self.add_net(new_netname)
            #print("adding", new_net)

        #print("netname_map:", netname_map)

        for sub_inst in inst.cell.find_instance():
            new_inst = copy.copy(sub_inst)
            new_inst.name = inst.name + "/" + new_inst.name
            new_inst.pins = []
            #print("\nadding", new_inst)
            #self.add_instance(new_inst)
            self.instances[new_inst.name.lower()] = new_inst #FIXME: api
            for pin in sub_inst.find_pin():
                #print("\nprocessing pin:", pin)
                new_port = copy.copy(pin.port)
                #print("looking up:", pin.net.name, "=>", netname_map[pin.net.name])
                new_net  = self.find_net(netname_map[pin.net.name])
                new_pin  = Pin(new_port, new_inst, new_net)
                new_inst.add_pinobj(new_pin)
                #print("adding new pin:", new_pin)

        del self.instances[inst.name.lower()]

    def flatten_cell(self, max_depth=1000):
        for depth in range(max_depth):
            hier_insts = [inst for inst in self.find_instance() if inst.ishier]
            #print("depth:", depth, [i.name for i in hier_insts])
            if len(hier_insts) == 0:
                return
            for inst in hier_insts:
                self.flatten_instance(inst)

    def search_scope(self, cellname):
        search_path = self.scope_path[:]
        search_path.append(self)
        search_path.reverse()
        for cell in search_path:
            try:
                return cell.find_cell(cellname)
            except KeyError:
                continue
        raise KeyError(cellname)

    def search_scope_prim(self, primname):
        search_path = self.scope_path[:]
        search_path.append(self)
        search_path.reverse()
        for cell in search_path:
            try:
                return cell.find_prim(primname)
            except KeyError:
                continue
        raise KeyError(primname)

    def link(self):
        #resolve_references
        #bind
        pass

    def resolve_refs(self): # link_design link_cell link_ckt
        for cell in self.find_cell():
            cell.resolve_refs()

        #cache = {}
        #count = 0
        hier_insts = [inst for inst in self.find_instance() if inst.ishier]
        for inst in hier_insts:
        #for inst in self.find_instance():
            #count += 1
            #if count % 10 == 0:
            #print("Resolving refs... inst: %s/%s" % (self.full_name(),
            #                                          inst.name), end='')
            if inst.cell is None:
                #try:
                #    cell = cache[inst.cellname]
                #except KeyError:
                try:
                    cell = self.search_scope(inst.cellname)
                    #cache[inst.cellname] = cell
                except KeyError:
                    raise LinkingError("failed to to resolve ref '%s' of '%s' in cell '%s'" %
                                       (inst.cellname, inst.name, self.full_name()))

            #self.bind_inst2cell(inst, cell)
            inst.cell = cell
            #if count % 10 == 0:
            #print("=> cell:", inst.cell.full_name())


    def __repr__(self):
        lev = len(self.scope_path)
        indent = " " * 4

        r  = "%s(%s) {\n" % (self.__class__.__name__, self.full_name())
        for port in self.ports.values():
            r += indent*(lev+1) + str(port) + "\n"
        r += indent*(lev+1) + "Params(" + str(self.params) + ")\n"
        for net in self.nets.values():
            r += indent*(lev+1) + str(net) + "\n"
        for instance in self.instances.values():
            r += indent*(lev+1) + str(instance) + "\n"
        for pin in self.find_pin():
            r += indent*(lev+1) + str(pin) + "\n"
        for cell in self.cells.values():
            r += indent*(lev+1) + str(cell) + "\n"
        r += indent*lev + "}"
        return r

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

    def __init__(self, name=None, params=None):
        super(Ckt, self).__init__(name, params)
        self._reader_cache = {}

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
