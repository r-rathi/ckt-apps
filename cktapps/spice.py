#-------------------------------------------------------------------------------
from __future__ import absolute_import
from __future__ import print_function

import re, collections

#-------------------------------------------------------------------------------
RE_BLANK_LINE       = re.compile(r"^\s*$")
RE_COMMENT_LINE     = re.compile(r"^\s*[*$].*$")
RE_TRAILING_COMMENT = re.compile(r"\s*[$].*$")

#-------------------------------------------------------------------------------
class SyntaxError(Exception): pass

#-------------------------------------------------------------------------------
def read_spice_line(file):
    """
    Reads a Spice file line-by-line, unwrapping the line continuations (+) in
    the process. Every invocation returns a new line.
    """
    line_num = 0;
    #with open(filename, "r") as file: 
    #    line = file.readline()
    for line in file:
        line_num += 1
        line = line.rstrip('\n')

        for next_line in file:
            line_num += 1
            next_line = next_line.rstrip('\n')

            if next_line and next_line[0] == '+':
                if (RE_BLANK_LINE.match(line) or
                    RE_COMMENT_LINE.match(line)) :
                    raise SyntaxError("invalid line continuation: %s, %s\n%s" %
                                           (filename, line_num, next_line))
                line += next_line[1:]
                continue
            else:
                yield (line, file.name, line_num-1)
                line = next_line
        yield (line, file.name, line_num)

def read_spice(ckt, file, spice_reader=None):
    if spice_reader is None:
        spice_reader = SpiceReader(ckt)
    spice_reader.read(file)
    
#def write_spice_line(filename, max_line_size=None):
    #file = open(filename, "w")
def write_spice(cell, file=None):
    spice_writer = SpiceWriter(cell) #, file)
    spice_writer.emit_cell()

class SpiceWriter(object):
    def __init__(self, cell):
        self.cell = cell
        self.file = None
        self.indent_stack = []

    def reset_indent(self):
        self.indent_stack = []
        self.indent_pos = 0
        self.new_line = True

    def next_line(self):
        print(file=self.file)
        self.new_line = True

    def indent(self, by=1, width=4):
        self.indent_stack.append(self.indent_pos)
        self.indent_pos += by * width

    def dedent(self):
        self.indent_pos = self.indent_stack.pop()

    def emit(self, string, sep=' '):
        if self.new_line:
            prefix = ' ' * self.indent_pos
            self.new_line = False
        else:
            prefix = sep

        print(prefix + string, end='', file=self.file)

    def emitln(self, string, sep=' '):
        self.emit(string, sep)
        self.next_line()

    def emit_cell(self):
        self.reset_indent()
        self.emit_header()
        self.emit_instances()
        #self.emit_cells() # TODO: handle recursive cell decls.
        self.emit_trailer()

    def emit_header(self):
        self.emit('.subckt')
        self.emit(self.cell.name)
        self.emit_ports()

    def emit_trailer(self):
        self.emit('.ends')
        self.emitln(self.cell.name)

    def emit_ports(self):
        portnames = [port.name for port in self.cell.find_port()]
        self.emitln(' '.join(portnames))

    def emit_instances(self):
        for inst in self.cell.find_instance():
            self.emit_instance(inst)

    def emit_instance(self, inst):
        if inst.cellname.lower() in ['c']: #, 'nch', 'pch']:
            self.emit('c' + inst.name)
        else:
            self.emit('x' + inst.name)

        inst_netnames = [pin.net.name for pin in inst.find_pin()]
        self.emit(' '.join(inst_netnames))

        if inst.cellname.lower() in ['c']: #, 'nch', 'pch']:
            self.emitln(inst.params['cap'])
        else:
            self.emit(inst.cellname)
            for param, val in inst.params.items():
                self.emit('%s=%s' % (param, val))
            self.emitln('', sep='')

#-------------------------------------------------------------------------------
class SpiceReader(object):
    mos_models = ['nch', 'pch']
    def __init__(self, ckt):
        self.ckt = ckt
        self._cell_stack = [ckt]
        self._current_cell = ckt

    def read(self, file):
        for (line, filename, line_num) in read_spice_line(file):
            orig_line = line

            if (RE_BLANK_LINE.match(line) or
                RE_COMMENT_LINE.match(line)):
                continue

            line = RE_TRAILING_COMMENT.sub("", line)

            line = line.split()

            if line[0].lower() == ".subckt":
                params = collections.OrderedDict()
                non_params = []
                for item in line:
                    if re.search("=", item):
                        lhs, rhs = item.split("=")
                        params[lhs] = rhs
                    else:
                        non_params.append(item)

                cellname = non_params[1]
                portnames = non_params[2:]

                cell = self._add_cell(cellname, params=params)
                self._push_cell_scope(cell)

                for portname in portnames:
                    self._add_port(portname)
                    self._add_net(portname)

            if line[0].lower() == ".ends":
                try:
                    self._pop_cell_scope()
                except IndexError:
                    raise SyntaxError("keyword '.ends' unexpected here: %s, %s\n%s" %
                                           (filename, line_num, orig_line))

            elif line[0][0].lower() == "m" or \
                 line[0][0].lower() == "x" and \
                 len(line) > 5 and  line[5].lower() in self.mos_models:
                mname, s, g, d, b, model = line[0:6]
                if mname[0].lower() == "x":
                    mname = mname[1:]

                #params = line[6:]
                params = collections.OrderedDict()
                non_params = []
                for item in line:
                    if re.search("=", item):
                        lhs, rhs = item.split("=")
                        params[lhs] = rhs
                    else:
                        non_params.append(item)

                net_s = self._add_net(s)
                net_g = self._add_net(g)
                net_d = self._add_net(d)
                net_b = self._add_net(b)

                inst = self._add_instance(mname, model, params=params)

                self._add_pin('s', inst, net_s)
                self._add_pin('g', inst, net_g)
                self._add_pin('d', inst, net_d)
                self._add_pin('b', inst, net_b)

            elif line[0][0].lower() == "c":
                cname, plus, minus, cap = line
                params = dict(cap=cap)

                net_plus = self._add_net(plus)
                net_minus = self._add_net(minus)

                inst = self._add_instance(cname, 'c', params=params)

                self._add_pin('plus', inst, net_plus)
                self._add_pin('minus', inst, net_minus)

            elif line[0][0].lower() == "x":
                params = collections.OrderedDict()
                non_params = []
                for item in line:
                    if re.search("=", item):
                        lhs, rhs = item.split("=")
                        params[lhs] = rhs
                    else:
                        non_params.append(item)

                instname = non_params[0][1:]
                cellname = non_params[-1]
                netnames = non_params[1:-1]

                inst = self._add_instance(instname, cellname, params=params)
                inst.ishier = True

                for netname in netnames:
                    net = self._add_net(netname)
                    self._add_pin(None, inst, net)

    def _push_cell_scope(self, cell):
        self._cell_stack.append(self._current_cell)
        self._current_cell = cell

    def _pop_cell_scope(self):
        prev_cell = self._current_cell
        self._current_cell = self._cell_stack.pop()
        return prev_cell

    def _add_cell(self, *args, **kwargs):
        parent_cell = self._current_cell
        cell = parent_cell.add_cell(*args, **kwargs)
        cell.scope_path = parent_cell.scope_path + [parent_cell]
        return cell

    def _add_port(self, *args, **kwargs):
        parent_cell = self._current_cell
        return parent_cell.add_port(*args, **kwargs)

    def _add_net(self, *args, **kwargs):
        parent_cell = self._current_cell
        return parent_cell.add_net(*args, **kwargs)

    def _add_instance(self, *args, **kwargs):
        parent_cell = self._current_cell
        return parent_cell.add_instance(*args, **kwargs)

    def _add_pin(self, *args, **kwargs):
        parent_cell = self._current_cell
        return parent_cell.add_pin(*args, **kwargs)

