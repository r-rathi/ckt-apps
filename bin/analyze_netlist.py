#!/usr/bin/env python

#-------------------------------------------------------------------------------
import os
import sys

bin_dir = os.path.dirname(os.path.abspath(__file__))
pkg_dir = os.path.abspath(os.path.join(bin_dir, ".."))
sys.path.append(pkg_dir)

#-------------------------------------------------------------------------------
import argparse
import collections

import cktapps
from cktapps import apps
from cktapps.formats import spice

#-------------------------------------------------------------------------------
def main(args=None):
    parser = argparse.ArgumentParser(description="Analyze netlist")

    parser.add_argument('spice_files', metavar='file', nargs='+',
                        type=argparse.FileType('r'), help='spice netlist file(s)')

    parser.add_argument('--lib', type=argparse.FileType('r'),
                        help='lib file(s) with model (e.g. nch, pch) defintions')

    parser.add_argument('--cell', help='name of the cell to be analyzed '
                                       '(top cell by default)')

    arg_ns = parser.parse_args(args)

    #---------------------------------------------------------------------------
   
    ckt = cktapps.Ckt("$root")

    if arg_ns.lib:
        ckt.read_spice(arg_ns.lib)

    for spice_file in arg_ns.spice_files:
        ckt.read_spice(spice_file)

    ckt.link(ignore_link_errors=True)
    #link_done = False
    #while not link_done:
    #    try:
    #        ckt.link()
    #        link_done = True
    #    except cktapps.core.LinkError, e:
    #        print(e)

    #if not link_done:
    #    raise cktapps.core.LinkError("failed to link the circuit.")

    #topcellnames = [cell.name for cell in ckt.get_topcells()]
    #print "Top cells: %s" % topcellnames

    if arg_ns.cell:
        cell = ckt.get_cell(arg_ns.cell)
    else:
        topcells = ckt.get_topcells()
        if topcells:
            cell = topcells[0]
        else:
            cell = ckt

    #print cell

    #print "-"*80
    #apps.report_hierarchy(cell)

    #ckt.write_spice(cell)

    #print "-"*80
    cell.ungroup(flatten=True)
    #print cell
    #ckt.write_spice(cell)

    #print "-"*80
    lib = arg_ns.lib.name
    netlists = [f.name for f in arg_ns.spice_files]
    #apps.report_net(cell, lib, netlists)

    #print "-"*80
    #apps.report_hierarchy(cell)
    return ckt

#-------------------------------------------------------------------------------
if __name__ == "__main__":
    ckt = main()

