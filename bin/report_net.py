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
    parser = argparse.ArgumentParser(description="Report net fanout")

    parser.add_argument('spice_files', metavar='file', nargs='+',
                        type=argparse.FileType('r'), help='spice netlist file(s)')

    parser.add_argument('--lib', nargs='+', type=argparse.FileType('r'),
                        help='lib file(s) with model (e.g. nch, pch) defintions')

    parser.add_argument('--cell', required=True,
                        help='name of the cell to be analyzed')

    arg_ns = parser.parse_args(args)

    #---------------------------------------------------------------------------
   
    ckt = cktapps.Ckt("")

    if arg_ns.lib:
        for lib_file in arg_ns.lib:
            spice.read_spice(ckt, lib_file)

    for spice_file in arg_ns.spice_files:
        spice.read_spice(ckt, spice_file)

    ckt.resolve_refs()

    cellname = arg_ns.cell

    cell = ckt.find_cell(cellname)
    #print cell

    spice.write_spice(cell)

    print "-"*80
    cell.flatten_cell()
    #print cell
    spice.write_spice(cell)


    print "-"*80

    apps.report_net(cell)

#-------------------------------------------------------------------------------
if __name__ == "__main__":
    main()

