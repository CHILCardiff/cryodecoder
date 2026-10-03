.. _blocks_level3:

Level 3 blocks
==============

This page describes Level 3 (L3) or 'Context' blocks in the CHIL packet format. These are the 'top-level' component of a CHIL packet and describe the context for data that has been recorded. This includes the identify of the receiver that was used, the time at which it was recorded and the sequence number in which it has been recorded.

As with all the block formats, each L3 block begins with an identifier and packet length. To allow for longer combinations of L2 and L1 blocks, the L3 packet length is 2 bytes in length.

:code:`D` - Data context
^^^^^^^^^^^^^^^^^^^^^^^^
.. csv-table::
    :header: Length (bytes),Description,Example
    :widths: auto

    1,Block indentifier,'D'
    2,Block length,Variable
    4,Receiver ID,'P001'
    4,Timestamp (Unix encoded),827650680
    1,Receiver sequence number,0 to 255
    ?,Payload of L2 blocks,See Level 2 - Origin blocks

:code:`H` - Housekeeping context
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. csv-table::
    :header: Length (bytes),Description,Example
    :widths: auto
    
    1,Block indentifier,'H'
    2,Block length,Variable
    4,Receiver ID,'T001'
    4,Timestamp (Unix encoded),1287605400
    1,Housekeeping sequence number,0 to 255
    ?,Payload of L2 blocks,See Level 2 - Origin blocks

Compatibility with older packet formats
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Older CHIL packet formats begin with the two-byte identifiers `C0`, `C1`, `W1` and `W2` for different generations of Cryoegg (`C`) and Cryowurst (`W`) packets respectively. We reserve the values `C` and `W` for the identifier of an L3 block so that if this value is encountered, it can be decoded using the original format.

The original packet formats are described :doc:`here <legacy>`.`