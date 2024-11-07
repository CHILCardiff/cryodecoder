.. _stored_data_packets:

Stored data packets
===================

All packets transmitted by satellite link or stored by the receiver are formatted in a binary format.  The type of packet can be established from a two character ASCII identifier which make up the first two bytes of a data packet. Valid values for these identifiers are tabulated below:

+------------+----------------------+-----------------------------------------+
| Identifier | Packet Type          | Notes                                   |
+============+======================+=========================================+
| C0         | Cryoegg 2019         | Original 2019 packet format, no longer  |
|            |                      | in use.                                 |
+------------+----------------------+-----------------------------------------+
| C1         | Cryoegg 2022         | Curently in use. Cryoegg data is        |
|            |                      | unchanged from C1. Contains additional  |
|            |                      | data from receiver (pressure,           |
|            |                      | temperature, battery voltage)           |
+------------+----------------------+-----------------------------------------+
| W1         | Cryowurst 2023       | Original Cryowurst packet format, no    |
|            |                      | longer in use                           |
+------------+----------------------+-----------------------------------------+
| W2         | Cryowurst 2024       | Currently in use, includes additional   |
|            |                      | accelerometer data from IMU.            |
+------------+----------------------+-----------------------------------------+

Cryoegg
-------
All Cryoegg packets begin with **C** and carry temperature, conductivity and pressure data.

C0 Packets
^^^^^^^^^^

The format of data within a **C0** packet is given below.  All multi-byte fields are **little endian** unless otherwise specified.  Each C0 packet is a total of **25 bytes** in length.

.. csv-table::
   :file: format_C0.csv
   :header-rows: 1

C1 Packets
^^^^^^^^^^
The format of data within a **C1** packet is given below.  All multi-byte fields are **little endian** unless otherwise specified.  Each C1 packet is a total of **40 bytes** in length.

.. csv-table::
   :file: format_C1.csv
   :header-rows: 1

Cryowurst 
---------
All Cryowurst packets begin with **W** and carry temperature, conductivity, pressure and orientation data.

W1 Packets
^^^^^^^^^^
The format of data within a **W1** packet is given below.  All multi-byte fields are **big endian** unless otherwise specified.  Each W1 packet is a total of **56 bytes** in length.

.. csv-table::
   :file: format_W1.csv
   :header-rows: 1

W2 Packets
^^^^^^^^^^
The format of data within a **W2** packet is given below.  All multi-byte fields are **big endian** unless otherwise specified.  Each W2 packet is a total of **62 bytes** in length.  The W2 packet was introduced in August 2024 to allow for comparison between the TDK ICM 20948 and TILT-05 the accelerometer data.

.. csv-table::
   :file: format_W2.csv
   :header-rows: 1

Hydrobean
---------
Hydrobean packets are not yet supported.
