#-------------------------------------------------------------------------------
from __future__ import print_function
import collections

#-------------------------------------------------------------------------------
def report_net(cell):
    net_info = collections.OrderedDict()
    for net in cell.nets.all():
        net_info[net.name] = dict(drivers=[], loads=[], caps=[])

    for inst in cell.instances.all():
        for pin in inst.pins.all():
            if pin.port.name in ('s', 'd'):
                net_info[pin.net.name]['drivers'].append(pin.instance)
            elif pin.port.name == 'g':
                net_info[pin.net.name]['loads'].append(pin.instance)
            elif pin.instance.cellname == 'c':
                net_info[pin.net.name]['caps'].append(pin.instance)

    for netname, info in net_info.items():
        drivers = info['drivers']
        loads   = info['loads']
        caps    = info['caps']
        print("net:", netname, end=' ')
        print("caps:", ",".join([i.name for i in caps]), end=' ')
        print("drivers:", ",".join([i.name for i in drivers]), end=' ')
        print("loads:", ",".join([i.name for i in loads]))

    print("fo:",
          "net".ljust(12),
          "cnet".rjust(8),
          "cload".rjust(8),
          "cdriver".rjust(8),
          "fanout=(cnet+cload)/cdriver")

    print("fo:",
          "---".ljust(12),
          "----".rjust(8),
          "-----".rjust(8),
          "-------".rjust(8),
          "---------------------------")

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

        print("fo:", netname.ljust(12),
                     ("%1.2g" % net_cap).rjust(8),
                     ("%1.2g" % load_cap).rjust(8),
                     ("%1.2g" % driver_cap).rjust(8),
                     ("%.1f" % fanout).rjust(8), sep=" ")

#-------------------------------------------------------------------------------
def report_hierarchy(cell):
    print("Hierarchy report for cell: %s" % cell.name)
    print(cell.name)
    _print_cell_hierarchy(cell, 0) 

def _print_cell_hierarchy(cell, indent):
    for inst in cell.instances.all():
        print("%s|-- %s (%s)" % (' ' * 4  * indent, inst.name, inst.cellname))
        if inst.ishier:
            _print_cell_hierarchy(inst.cell, indent + 1)
            print()

