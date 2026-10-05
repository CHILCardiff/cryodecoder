API: cryodecoder
=================

Submodules
----------
Functionality of the cryodecoder module is split into several submodules. The :py:mod:`blocks <cryodecoder.blocks>` submodule defines the blocks and subblocks which make up CHIL packets and provides an interface to parse and interact with them. The :py:mod:`parser <cryodecoder.parser>` submodule provides defines a parsing algorithm for CHIL data and various interfaces to parse and log data from files and USB data streams. The :py:mod:`cloudloop <cryodecoder.cloudloop>` submodule provides functionality to list and download packets from the IOT provider *Cloudloop*.

.. toctree::
    :titlesonly: 

    blocks
    cloudloop
    parser
    exceptions

Top-level functions
-------------------
There are several 'utility functions' in the top level of the :py:mod:`cryodecoder` module. 

.. automodule:: cryodecoder
    :members: