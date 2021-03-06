Ckt-apps: Circuit Design and Analysis Applications
==================================================

**Ckt-apps** is a suite of circuit design and anaysis (EDA) applications as well as the package (library) itself on which the applications are based.

Applications
------------
The end-user applications are in the *bin* directory. Currently, following applications are provided:
- `bin/report_net.py` - Report nets in the design with summary of wire, driver, and load caps and fanouts.

The cktapps package
-------------------
The architecture of `cktapps` is very modular and extensible. The main componets are:
- `core` : At the _core_ of ckt-apps is a circuit netlist database that represents the basic circuit elements and their connectivity. The database supports hierarchical designs, and can be queried as well as modified through the core API interface.
- `formats` : Contains netlist format specific modules that provide reading and writing in addition to any other format specific functionality. Following formats are currently supported:
  * `spice`
- `apps` : Contains a library of design and analysis utilities in the form of importable functions, classes, and modules. The end-user scripts in the *bin* directory are essentially wrappers that provide a command-line interface and internally use one or more components from the the *apps* package to provide the end-user functionality.

Installation
------------
Clone the repository:

    $git clone https://github.com/r-rathi/ckt-apps

Or, download the tarball:

    $curl -L -o ckt-apps.tar.gz https://api.github.com/repos/r-rathi/ckt-apps/tarball

Or, go to https://github.com/r-rathi/ckt-apps and click on the ZIP button.

Usage
-----
The applications should be called directly from the package directory:

    $ /path/to/ckt-apps/bin/report_net.py -h

Or, if python is not in you path, then:

    $ /path/to/python /path/to/ckt-apps/bin/report_net.py -h

Example
-------
`bin/report_net.py` reports the wire, driver, and load capacitances and the driver fanout for all the nets in a specified cell. If no cell is given, then the (first) top-cell is used. Using the lib and netlist from `ckt-apps/test_data`:

    $ bin/report_net.py --lib test_data/lib.sp test_data/test1.sp

    ****************************************
    Report : net
            -capacitance=True
            -fanout=True
            -sortby=fanout, reversesort=True
    Cell   : buf
    Date   : 02:04AM April 08, 2013
    ****************************************
    
    Lib     : test_data/lib.sp
    Netlist : test_data/test1.sp
    
    Fields:
    - net     : net name
    - cwire   : wire capacitance (fF)
    - cload   : load (gate connected transistors) capacitance (fF)
    - cdriver : driver (src/drain connected transistors) capacitance (fF)
    - fanout  : fanout of the driver = cout/cin = (cwire + cload)/cdriver
    
    --------------------------------------------
      net     cwire   cload   cdriver   fanout  
    --------------------------------------------
      n2        8.0     0.4       0.2     42.0  
      b2/n2     5.0     0.2       0.2     26.0  
      b3/n2     9.0     0.4       0.4     23.5  
      vss      21.0     0.0       0.9     23.3  
      b1/n2     4.0     0.4       0.2     22.0  
      vdd      15.0     0.0       0.9     16.7  
      y         6.0     0.0       0.4     15.0  
      n1        3.0     0.2       0.4      8.0  
      a         1.0     0.2       0.0      0.0  
    --------------------------------------------

License
-------
Copyright (c) 2013 Rohit Rathi &lt;rrathi.appdev@gmail.com&gt;

Ckt-apps is provided under the MIT License. See the `LICENSE` file for details.
