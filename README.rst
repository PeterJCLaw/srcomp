SRComp
======

|Build Status| |Docs Status|

Yet Another attempt at some Competition Software for `Student
Robotics <http://srobo.org>`__.

The `SRComp wiki <https://github.com/PeterJCLaw/srcomp/wiki>`__ provides
an overview of the suite as a whole.

This repository provides a python API to accessing information about the
state of the competition. That *compstate* is stored as a collection of
YAML files in a git repository. This allows the state of the competition
to be managed in isolation from the software while still providing
consistent representations of that state.

Usage
-----

Python clients should submodule this repo and then import it. Only the
``SRComp`` is class directly exposed, and it should be constructed
around the path to a local working copy of a *compstate repo*.

.. code:: python

    from srcomp import SRComp
    comp = SRComp('/path/to/compstate')

**Web clients** should look at using the HTTP API provided by
`srcomp-http <https://github.com/PeterJCLaw/srcomp-http>`__
rather than implementing their own intermediary.

There is also a **command line** interface which provides utilities for
managing a *compstate repo*:
`srcomp-cli <https://github.com/PeterJCLaw/srcomp-cli>`__.

See the
`dummy-comp <https://github.com/PeterJCLaw/dummy-comp>`__
for an example of the structure and values expected in a *compstate
repo*.

Requirements
------------

-  Python 2.7
-  python-dateutil
-  PyYAML
-  nose (for testing)
-  mock (for testing)

Test with
---------

``./run-tests``

.. |Build Status| image:: https://travis-ci.org/PeterJCLaw/srcomp.png?branch=master
   :target: https://travis-ci.org/PeterJCLaw/srcomp

.. |Docs Status| image:: https://readthedocs.org/projects/srcomp/badge/?version=latest
   :target: http://srcomp.readthedocs.org/
