Ckt-apps: Circuit Design and Analysis Applications
==================================================

**Ckt-apps** is a collection of circuit design and anaysis applications as well as the package (library) itself on which the applications are based.

Applications
------------
The end-user applications are in the *bin* directory. Currently, following following applications are provided:
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

License
-------
Copyright (c) 2013 Rohit Rathi &lt;rrathi.appdev@gmail.com&gt;

Ckt-apps is provided under the MIT License. See the `LICENSE` file for details.
