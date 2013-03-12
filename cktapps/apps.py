#-------------------------------------------------------------------------------
from __future__ import print_function
import collections

#-------------------------------------------------------------------------------
def report_net(cell):
    net_info = collections.OrderedDict()
    for net in cell.find_net():
        net_info[net.name] = dict(drivers=[], loads=[], caps=[])

    for inst in cell.find_instance():
        for pin in inst.find_pin():
            if pin.port.name in ('s', 'd'):
                net_info[pin.net.name]['drivers'].append(pin.instance)
            elif pin.port.name == 'g':
                net_info[pin.net.name]['loads'].append(pin.instance)
            elif pin.instance.cell.name == 'c':
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
            net_cap += float(i.params['cap'])

        for i in drivers:
            w = i.params.get('w') or i.params.get('W')
            l = i.params.get('l') or i.params.get('L')
            driver_cap += float(w) * float(l) * 0.05

        for i in loads:
            w = i.params.get('w') or i.params.get('W')
            l = i.params.get('l') or i.params.get('L')
            load_cap += float(w) * float(l) * 0.05

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
