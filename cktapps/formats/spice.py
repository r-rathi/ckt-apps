"""
Functions and classes to handle spice format

Classes:

    SpiceReader
    SpiceWriter

Functions:

    read_spice_line(fileobj) -> list
    split_spice_line(list) -> list
    parse_spice_line(list) -> dic

"""

#-------------------------------------------------------------------------------
from __future__ import absolute_import
from __future__ import print_function

import time
import re, collections

#-------------------------------------------------------------------------------
RE_BLANK_LINE       = re.compile(r"^\s*$")
RE_COMMENT_LINE     = re.compile(r"^\s*[*$].*$")
RE_TRAILING_COMMENT = re.compile(r"\s*[$].*$")

#-------------------------------------------------------------------------------
class SyntaxError(Exception): pass

class ParserError(Exception): pass

#-------------------------------------------------------------------------------
def read_line(f):
    """Reads a Spice file line-by-line, unwrapping the line continuations (+)
    in the process. Every invocation returns a tuple (line, filename, lineno)

    This is just a module level wrapper over the Reader.read_line() method.
    """
    return Reader.read_line(f)

#def write_spice_line(filename, max_line_size=None):
    #file = open(filename, "w")
def write_spice(cell, file=None):
    spice_writer = SpiceWriter(cell) #, file)
    spice_writer.emit_cell()

#-------------------------------------------------------------------------------
class Reader(object):
    def __init__(self, ckt):
        self.ckt = ckt
        self._cell_stack = [ckt]
        self._current_cell = ckt
                        
    @classmethod
    def read_line(cls, f):
        """
        Reads a Spice file line-by-line, unwrapping the line continuations (+) in
        the process. Every invocation returns a tuple (line, filename, lineno)
        """
        lineno = 0;
        for line in f:
            lineno += 1
            line = line.rstrip('\n')

            for next_line in f:
                lineno += 1
                next_line = next_line.rstrip('\n')

                if next_line and next_line[0] == '+':
                    if (RE_BLANK_LINE.match(line) or
                        RE_COMMENT_LINE.match(line) or
                        RE_TRAILING_COMMENT.search(line)):
                        raise SyntaxError("invalid line continuation: %s, %s\n-> %s" %
                                               (f.name, lineno, next_line))
                    line = line.rstrip() + " " + next_line[1:].lstrip()
                    continue
                else:
                    yield (line, f.name, lineno-1)
                    line = next_line
            yield (line, f.name, lineno)

    @classmethod
    def _tokenize(cls, line):
        """ Split a spice line into tokens """

        # add spaces around comment begin chars '*' or '$'
        line = re.sub(r'\*', ' * ', line)
        line = re.sub(r'\$', ' $ ', line)

        # remove spaces around '='
        line = re.sub(r'\s*=\s*', '=', line)

        # remove all spaces from within "..." (spice parameter expressions)
        def rm_space(matchobj):
            return re.sub(r'\s+', '', matchobj.group(0))

        line = re.sub(r'"([^"]*)"', rm_space, line)

        return line.split()

    @classmethod
    def _parse(cls, tokens, skipcomments=True):
        """
        Parses a tokenized spice line and returns a statement-tree:

            pstmt = {'type'   : [<major>, <minor>]
                     'args'   : [...]
                     'kwargs' : OrderedDict(...),
                     'comment': '...'
                    }

            or None for blank or comment lines.

        If skipcomments is False, then pstmt is returned.
        """

        if not tokens:  # skip blank line
            return None

        if tokens[0] in ['*', '$']:
            if skipcomments: return None
            type = ['comment', tokens[0]]
        elif tokens[0].startswith('.'):
            type = ['control', tokens[0][1:]]
        else:
            type = ['element', tokens[0][0]]

        args = []
        kwargs = collections.OrderedDict()
        comment = ''

        args_done = False
        for pos, tok in enumerate(tokens):
            if tok in ['*', '$']:
                comment = " ".join(tokens[pos:])
                break
            elif '=' in tok:
                k, v = tok.split('=')
                if not v:
                    raise SyntaxError("missing parameter value: %s=?" % k)

                kwargs[k] = v
                args_done = True
            else:
                if args_done:
                    raise SyntaxError("unexpected token '%s' at pos '%s'"
                                      % (tok, pos))
                args.append(tok)

        return dict(type=type, args=args, kwargs=kwargs, comment=comment)

    def read(self, f):
        for (line, fname, lineno) in self.read_line(f):
            try:
                tokens = self._tokenize(line)
                pstmt = self._parse(tokens)

            except SyntaxError, e:
                raise SyntaxError("%s [%s, %s]\n-> %s" %
                                  (e.msg, fname, lineno, line))

            if pstmt is None: continue

            major, minor = pstmt['type']

            # Skip comments for now
            if major == 'comment': continue

            try:
                self._process_stmt[major][minor](self, pstmt)
            except KeyError:
                raise ParserError(
                    "unrecognized type '%s/%s' [%s, %s]\n-> %s" %
                    (major, minor, fname, lineno, stmt))


    def read_old(self, file):
        t0 = time.time()
        for (line, filename, lineno) in read_spice_line(file):
            orig_line = line

            dl = 1000
            if lineno % dl == 0:
                t1 = time.time()
                dt = (t1 - t0)*1e6 # usec
                t0 = t1
                print("%s usec/line: %s : %s" % (dt/dl, lineno, line))

            if (RE_BLANK_LINE.match(line) or
                RE_COMMENT_LINE.match(line)):
                continue

            line = RE_TRAILING_COMMENT.sub("", line)

            line = line.split()
            len_line = len(line)
            card_type = line[0][0].lower()


            if card_type == ".":
                self._parse_kw_line(line)

            elif card_type == "m" or card_type == "x" and \
                 len_line > 5 and  line[5].lower() in self.ckt.macromodels:
            #elif card_type in ('m', 'x'): 
                self._parse_mx(line)

            elif card_type == 'c':
                self._parse_c(line)

            elif card_type == 'x':
                self._parse_x(line)

    #---------------------------------------------------------------------------
    def _process_subckt(self, pstmt):
        args = pstmt['args']
        params = pstmt['kwargs']

        cellname = args[1]
        portnames = args[2:]

        cell = self._add_cell(cellname, params=params)
        self._push_cell_scope(cell)

        for portname in portnames:
            self._add_port(portname)
            self._add_net(portname)

    def _process_ends(self, pstmt):
        try:
            self._pop_cell_scope()
        except IndexError:
            raise SyntaxError("keyword '.ends' unexpected here: %s, %s\n-> %s" %
                                   (filename, lineno, orig_line))

    def _process_macromodel(self, pstmt):
        args = pstmt['args']
        params = pstmt['kwargs']

        name, type = args[1:]
        macromodel = self._add_macromodel(name, type) #, params=params)
        self._push_cell_scope(macromodel)

    def _process_endmacromodel(self, pstmt):
        try:
            self._pop_cell_scope()
        except IndexError:
            raise SyntaxError(
                "keyword '.endmacromedel' unexpected here: %s, %s\n-> %s" %
                (filename, lineno, orig_line))

    def _process_param(self, pstmt):
        pass

    def _process_r(self, pstmt):
        pass

    def _process_c(self, pstmt):
        args = pstmt['args']
        params = pstmt['kwargs']

        cname, plus, minus, cap = args
        params.update(dict(cap=cap))

        net_plus = self._add_net(plus)
        net_minus = self._add_net(minus)

        inst = self._add_instance(cname, 'c', params=params)

        self._add_pin('plus', inst, net_plus)
        self._add_pin('minus', inst, net_minus)

    def _process_m(self, pstmt):
        args = pstmt['args']
        params = pstmt['kwargs']

        mname, s, g, d, b, model = args[0:6]
        if mname[0].lower() == "x":
            mname = mname[1:]

        net_s = self._add_net(s)
        net_g = self._add_net(g)
        net_d = self._add_net(d)
        net_b = self._add_net(b)

        inst = self._add_instance(mname, model, params=params)

        self._add_pin('s', inst, net_s)
        self._add_pin('g', inst, net_g)
        self._add_pin('d', inst, net_d)
        self._add_pin('b', inst, net_b)

    def _process_x(self, pstmt):
        args = pstmt['args']
        params = pstmt['kwargs']

        instname = args[0][1:]
        cellname = args[-1]
        netnames = args[1:-1]


        if cellname in self.ckt.macromodels:
            self._process_m(pstmt)
            return

        inst = self._add_instance(instname, cellname, params=params)
        inst.ishier = True

        for netname in netnames:
            net = self._add_net(netname)
            self._add_pin(None, inst, net)

    _process_stmt = {'control' : {'subckt'        : _process_subckt,
                                  'ends'          : _process_ends,
                                  'macromodel'    : _process_macromodel,
                                  'endmacromodel' : _process_endmacromodel,
                                  'param'         : _process_param,
                                 },
                     'element' : {'r' : _process_r,
                                  'c' : _process_c,
                                  'm' : _process_m,
                                  'x' : _process_x
                                 }
                    }

    #---------------------------------------------------------------------------
    def _push_cell_scope(self, cell):
        self._cell_stack.append(self._current_cell)
        self._current_cell = cell

    def _pop_cell_scope(self):
        prev_cell = self._current_cell
        self._current_cell = self._cell_stack.pop()
        return prev_cell

    #---------------------------------------------------------------------------
    def _add_macromodel(self, name, type): #*args, **kwargs):
        self.ckt.macromodels[name] = type
        return name

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

#-------------------------------------------------------------------------------
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

