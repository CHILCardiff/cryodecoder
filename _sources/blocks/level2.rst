.. _blocks_level2:

Level 2 blocks
==============

:code:`M` - Wireless MBus packet
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This block format describes payloads that have been received via the Wireless MBus modem. The UID from the MBUs packet format can be used to uniquely identify the instrument that has sent the data.

The :code:`M` block format has a 'wrapping' property in that the L1 blocks it describes are surrounded by data from the L2 block. This is because the RSSI byte is appended on to the transmitted L1 message by the Wireless MBus modem and we are avoiding manipulating the bitstream in the processing chain.

.. csv-table::
    :header: Length (bytes),Description,Example
    :widths: auto

    1,Block indentifier,'M'
    1,Block length,?? to ??
    1,Channel number,0 or 1
    1,MBus C-field,??
    2,MBus M-field (manufacturer ID),??
    4,MBus UID,0xCE249001
    1,MBus version,??
    1,MBUS device type,??
    1,MBus CI-field,??
    ?,Payload of L1 blocks,A, C, P from Cryoegg
    1,MBus received signal strength (RSSI),0 to 255

:code:`R` - Receiver sensors
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This block format indicates that the payload of sensor data originates from sensors directly connected to the reporting device (which is described by a parent L3 block). As an example, the datalogger can report environmental variables (temperature, humidity, etc.), orientation and system power status using the :code:`E`, :code:`B` and :code:`V` L1 blocks which describe parameters of the datalogger itself rather than the any instrument received by it.

.. csv-table::
    :header: Length (bytes),Description,Example
    :widths: auto

    1,Block indentifier,'R'
    1,Block length,Variable
    ?,Payload of L1 blocks,"E, B, V for datalogger"

