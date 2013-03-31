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
class Utils(object):
    pass

RE_BLANK_LINE       = re.compile(r"^\s*$")
RE_COMMENT_LINE     = re.compile(r"^\s*[*$].*$")
RE_TRAILING_COMMENT = re.compile(r"\s*[$].*$")

# Regex for spice number parsing based on:
#    http://search.cpan.org/~wimv/Number-Spice-0.011/Spice.pm
_RE_NUMBER = r'(?<!\w)[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[e][-+]?\d+)?'
_RE_SPICE_SUFFIX = r'(?:[a-df-z][a-z]*)|(?:e[a-z]+)'
RE_NUMBER = re.compile(_RE_NUMBER, re.IGNORECASE)
RE_SPICE_SUFFIX = re.compile(_RE_SPICE_SUFFIX, re.IGNORECASE)
RE_SPICE_NUMBER = re.compile(r'\s*(%s)(%s)?\s*' %
                             (_RE_NUMBER, _RE_SPICE_SUFFIX), re.IGNORECASE)

def spice_suffix_val(suffix):
    if suffix is None:
        return 1.0

    suffix_val = {'t'  :  1e12,      # tera
                  'g'  :  1e9,       # giga
                  'meg':  1e6,       # mega
                  'k'  :  1e3,       # kilo
                  'm'  :  1e-3,      # milli
                  'u'  :  1e-6,      # micro
                  'n'  :  1e-9,      # nano
                  'p'  :  1e-12,     # pico
                  'f'  :  1e-15,     # femto
                  'a'  :  1e-18      # atto
                 }
    suffix = suffix.lower()
    return suffix_val.get(suffix[:3]) or suffix_val.get(suffix[:1], 1.0)

def eval_spice_number(num_or_str):
    if isinstance(num_or_str, (int, float)):
        return num_or_str

    m = RE_SPICE_NUMBER.match(num_or_str)
    if m:
        number, suffix = m.groups()
        return float(number) * spice_suffix_val(suffix)
    else:
        return None

def replace_spice_number(s):
    def repl(m):
        return str(eval_spice_number(m.group()))
    return RE_SPICE_NUMBER.sub(repl, s)

#-------------------------------------------------------------------------------
class SyntaxError(Exception): pass
class ParserError(Exception): pass

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

        # remove spaces around '='
        line = re.sub(r'\s*=\s*', '=', line)

        # add spaces around comment begin chars '*' or '$'
        line = re.sub(r'\*', ' * ', line)
        line = re.sub(r'\$', ' $ ', line)

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
                                  (e.args[0], fname, lineno, line))

            if pstmt is None: continue

            major, minor = pstmt['type']

            # Skip comments for now
            if major == 'comment': continue

            try:
                self._process_stmt[major][minor](self, pstmt)
            except KeyError:
                raise ParserError(
                    "unrecognized type '%s/%s' [%s, %s]\n-> %s" %
                    (major, minor, fname, lineno, line))
            except SyntaxError, e:
                raise SyntaxError("%s [%s, %s]\n-> %s" %
                                  (e.args[0], fname, lineno, line))

    #---------------------------------------------------------------------------
    def _process_subckt(self, pstmt):
        args = pstmt['args']
        params = pstmt['kwargs']

        cellname = args[1]
        portnames = args[2:]

        cell = self._current_cell.add_cell(cellname, params=params)
        cell.scope_path = self._current_cell.scope_path + [self._current_cell]

        self._push_cell_scope(cell)

        for portname in portnames:
            self._current_cell.add_port(portname)
            self._current_cell.add_net(portname)

    def _process_ends(self, pstmt):
        try:
            self._pop_cell_scope()
        except IndexError:
            raise SyntaxError("keyword '.ends' unexpected here: %s, %s\n-> %s" %
                                   (filename, lineno, orig_line))

    def _process_macromodel(self, pstmt):
        args = pstmt['args']
        params = pstmt['kwargs']

        try:
            name, type = args[1:3]
        except ValueError:
            raise SyntaxError(".macromodel requires atleast 2 arguments")

        portnames = args[3:]

        self._current_cell.add_prim(name, type, portnames, params)

    def _process_param(self, pstmt):
        pass

    def _process_r(self, pstmt):
        pass

    def _process_c(self, pstmt):
        args = pstmt['args']
        params = pstmt['kwargs']

        instname = args[0]
        netnames = p, n = args[1:-1]
        cellname = 'c'
        params['c'] = args[-1]

        inst = self._current_cell.add_instance(instname, cellname, params=params)

        portnames = ['p', 'n']

        for netname, portname in zip(netnames, portnames):
            net = self._current_cell.add_net(netname)
            inst.add_pin(portname, net)

    def _process_m(self, pstmt):
        args = pstmt['args']
        params = pstmt['kwargs']

        instname = args[0]
        netnames = d, g, s, b = args[1:-1]
        cellname = args[-1]

        if instname[0].lower() == "x":
            instname = instname[1:]

        inst = self._current_cell.add_instance(instname, cellname, params=params)

        portnames = ['d', 'g', 's', 'b']

        for netname, portname in zip(netnames, portnames):
            net = self._current_cell.add_net(netname)
            inst.add_pin(portname, net)

    def _process_x(self, pstmt):
        args = pstmt['args']
        params = pstmt['kwargs']

        instname = args[0][1:]
        netnames = args[1:-1]
        cellname = args[-1]

        if cellname.lower() in self.ckt.prims:
            self._process_m(pstmt)
            return

        inst = self._current_cell.add_instance(instname, cellname, params=params)
        inst.ishier = True

        for netname in netnames:
            net = self._current_cell.add_net(netname)
            inst.add_pin(None, net)

    _process_stmt = {'control' : {'subckt'        : _process_subckt,
                                  'ends'          : _process_ends,
                                  'macromodel'    : _process_macromodel,
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
    def x_add_macromodel(self, name, type, params):
        self.ckt.macromodels[name] = type
        return name

    def x_add_cell(self, *args, **kwargs):
        parent_cell = self._current_cell
        cell = parent_cell.add_cell(*args, **kwargs)
        cell.scope_path = parent_cell.scope_path + [parent_cell]
        return cell

    def x_add_port(self, *args, **kwargs):
        parent_cell = self._current_cell
        return parent_cell.add_port(*args, **kwargs)

    def x_add_net(self, *args, **kwargs):
        parent_cell = self._current_cell
        return parent_cell.add_net(*args, **kwargs)

    def x_add_instance(self, *args, **kwargs):
        parent_cell = self._current_cell
        return parent_cell.add_instance(*args, **kwargs)

    def x_add_pin(self, *args, **kwargs):
        parent_cell = self._current_cell
        return parent_cell.add_pin(*args, **kwargs)

#-------------------------------------------------------------------------------
class Writer(object):
    def __init__(self, cell):
        self.cell = cell
        self.file = None
        self.indent_stack = []

    def write(self):
        self.emit_cell()

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
            self.emitln(inst.params['c'])
        else:
            self.emit(inst.cellname)
            for param, val in inst.params.items():
                self.emit('%s=%s' % (param, val))
            self.emitln('', sep='')

