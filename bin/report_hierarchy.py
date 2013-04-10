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
    parser = argparse.ArgumentParser(description="Report hierarchy")

    parser.add_argument('spice_files', metavar='file', nargs='+',
                        type=argparse.FileType('r'), help='spice netlist file(s)')

    parser.add_argument('--lib', type=argparse.FileType('r'),
                        help='lib file(s) with model (e.g. nch, pch) defintions')

    parser.add_argument('--cell', help='name of the cell to be analyzed')

    arg_ns = parser.parse_args(args)

    #---------------------------------------------------------------------------
   
    ckt = cktapps.Ckt()

    if arg_ns.lib:
        ckt.read_spice(arg_ns.lib)

    for spice_file in arg_ns.spice_files:
        ckt.read_spice(spice_file)

    ckt.link()

    if arg_ns.cell:
        cell = ckt.get_cell(arg_ns.cell)
    else:
        topcells = ckt.get_topcells()
        if topcells:
            cell = topcells[0]
        else:
            cell = ckt

    apps.report_hierarchy(cell)

#-------------------------------------------------------------------------------
if __name__ == "__main__":
    main()

