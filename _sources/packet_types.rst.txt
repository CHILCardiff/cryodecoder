CHIL instrument packet types
============================

There are various packet types associated with the different instruments developed at the CHIL lab, Cardiff.

Some packets are associated with individual instruments, while others are associated with how they were transmitted or received (i.e. VHF radio, satellite).

.. toctree::
    packet_types/sd_packets
    packet_types/satellite_packets

Packet Structure
----------------
At a base level, we are interested in unpacking a series of bytes into named data fields and converting to raw data values.  Examples of **data packets** are:

- Cryoegg data (temperature, conductivity, pressure, battery voltage) 
- Cryowurst data (temperature, conductivity, pressure, orientation, battery voltage) 
h
Because the instrumentation makes use of the Wireless M-Bus standard, these data packets are wrapped in an M-Bus frame which includes additional information regarding the origin of the packet, control flow and received signal strength.  The payload of an M-Bus packet to be processed could contain any of the **data packets**, or raw bytes from another source.

.. image:: _static/packet_types.png


Satellite and SD Packets
------------------------
Packets that are transmitted by satellite links or stored on the SD card of a datalogger are padded with auxiliary data from the receiver. 