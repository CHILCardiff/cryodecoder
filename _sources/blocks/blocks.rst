Instrument data protocol
========================

.. toctree::
    :hidden:

    level3
    level2
    level1
    legacy

Overview 
--------
The packet definitions for CHIL instruments are split into three levels **L1**, **L2** and **L3** packets which describe sensor data, the data origin and where it was collated. This abstraction is designed to allow for an extensible and adaptive packet format which can be applied to the different types of instruments within the CHIL family.

Level 1 (L1)
^^^^^^^^^^^^
Level 1 data encompasses direct observations from sensors or system variables, for example the temperature observed with a `TMP117`_ temperature sensor or the acceleration and magnetic field strength recorded in the XYZ axes by an `LSM303AGR`_ eCompass chip.

.. _TMP117: https://www.ti.com/lit/gpn/tmp117
.. _LSM303AGR: https://www.st.com/resource/en/datasheet/lsm303agr.pdf

Each variable length block begins with an identifier and a length field (each 1 byte) which describe the type of data to follow. The length field describes the length of the **L1** block in bytes, exclusive of the identifier and length field bytes.

.. csv-table:: Level 1 block format
    :header: "Parameter","Identifier","Length to follow","Payload"
    :widths: auto

    Length,1 byte,1 byte,N bytes
    *Example*,'K',9,"Pressure, temperature and scaling data"

Valid L1 identifiers and the expected structure of the payload are described :doc:`here <level1>`.

Level 2 (L2)
^^^^^^^^^^^^
Level 2 blocks provides information about the origin of the data described in Level 1 blocks. For example, a Cryoegg instrument equipped with temperature and pressure sensors is able to generate `C` and `P` L1 blocks but there is no information within these blocks that links the pressure and temperature measurements to that specific instrument. The purpose of an L2 block is to describe the origin of the L1 data. 

In the same manner as L1 blocks, L2 blocks begin with an identifier and length field which describe the type of origin block to follow. The length byte describes the length of the **L2** block in bytes, excluding the identifier byte and itself.

For example, data (as a collection of L1 blocks) transmitted by a Cryoegg using a Wireless MBus modem will be assigned at the receiver to an L2 block, which records variables such as the the unique ID (UID) of the instrument (i.e. `CE249001`), the radio channel it was recorded on and the received signal strength.

Valid L2 identifiers are described :doc:`here <level2>`.

Level 3 (L3)
^^^^^^^^^^^^

Valid L2 identifiers are described :doc:`here <level3>`.