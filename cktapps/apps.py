#-------------------------------------------------------------------------------
from __future__ import print_function
import collections
from packages import prettytable
import datetime

#-------------------------------------------------------------------------------
def report_net(cell, lib, netlists):
    net_info = collections.OrderedDict()
    for net in cell.all_nets():
        net_info[net.name] = dict(drivers=[], loads=[], caps=[])

    for inst in cell.all_instances():
        for pin in inst.all_pins():
            if pin.port.name in ('s', 'd'):
                net_info[pin.net.name]['drivers'].append(pin.instance)
            elif pin.port.name == 'g':
                net_info[pin.net.name]['loads'].append(pin.instance)
            elif pin.instance.refname == 'c':
                net_info[pin.net.name]['caps'].append(pin.instance)

    for netname, info in net_info.items():
        drivers = info['drivers']
        loads   = info['loads']
        caps    = info['caps']
        #print("net:", netname, end=' ')
        #print("caps:", ",".join([i.name for i in caps]), end=' ')
        #print("drivers:", ",".join([i.name for i in drivers]), end=' ')
        #print("loads:", ",".join([i.name for i in loads]))


    print(
"""****************************************
Report : net
        -capacitance=True
        -fanout=True
        -sortby=fanout, reversesort=True
Cell   : %s
Date   : %s
****************************************

Lib     : %s
Netlist : %s

Fields:
- net     : net name
- cwire   : wire capacitance (fF)
- cload   : load (gate connected transistors) capacitance (fF)
- cdriver : driver (src/drain connected transistors) capacitance (fF)
- fanout  : fanout of the driver = cout/cin = (cwire + cload)/cdriver
"""
    % (cell.name, datetime.datetime.now().strftime("%I:%m%p %B %d, %Y"),
       lib, "\n          ".join(netlists)))


    header = "net cwire cload cdriver fanout".split()
    report = prettytable.PrettyTable(header)

    report.vrules = prettytable.NONE
    report.align = 'r'
    report.align['net'] = 'l'
    report.float_format = '1.1'

    for netname, info in net_info.items():
        drivers = info['drivers']
        loads   = info['loads']
        caps    = info['caps']

        net_cap = 0
        driver_cap = 0
        load_cap = 0

        for i in caps:
            net_cap += float(i.params['c'])

        for i in drivers:
            cg = i.eval_param('cg')
            driver_cap += cg

        for i in loads:
            cg = i.eval_param('cg')
            load_cap += cg

        if driver_cap == 0.0:
            fanout = 0.0
        else:
            fanout = (net_cap + load_cap)/driver_cap

        #print("fo:", netname.ljust(12),
        #             ("%1.2g" % net_cap).rjust(8),
        #             ("%1.2g" % load_cap).rjust(8),
        #             ("%1.2g" % driver_cap).rjust(8),
        #             ("%.1f" % fanout).rjust(8), sep=" ")

        report.add_row([netname, net_cap*1e15, load_cap*1e15, driver_cap*1e15, fanout])

    rpt = report.get_string(sortby='fanout', reversesort=True)
    print(rpt)

#-------------------------------------------------------------------------------
def report_hierarchy(cell):
    print("Hierarchy report for cell: %s" % cell.name)
    print(cell.name)
    _print_cell_hierarchy(cell, 0) 

def _print_cell_hierarchy(cell, indent):
    for inst in cell.all_instances():
        print("%s|-- %s (%s)" % (' ' * 4  * indent, inst.name, inst.refname))
        if inst.ishier:
            _print_cell_hierarchy(inst.ref, indent + 1)
            print()

