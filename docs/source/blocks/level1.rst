.. _blocks_level1:

Level 1 blocks
==============

This page describes Level 1 (L1) blocks in the CHIL packet format. As a minimum, each L1 block must contain the block identifier (1 byte) which describes the type of the L1 block and a payload length (1 byte) which describes the number of bytes to follow.

List of valid L1 blocks
-----------------------
The table below provides an overview of all of the valid L1 blocks.

.. csv-table::
    :header: Block identifier,Length,Description
    :widths: auto

    'A' (0x41),12,LSM303AGR eCompass data.
    'B' (0x42),12,BMA400 accelerometer data.
    'C' (0x43),7,EC, temperature and auxiliary data.
    'E' (0x45),8,Temperature and pressure.
    'E' (0x45),12,Temperature, pressure and relative humidity with SHT30.
    'K' (0x4B),13,Keller pressure sensor data.
    'T' (0x54),10,CTi TILT-05 sensor data.
    'V' (0x56),2,Power system status from battery voltage sensor.
    'V' (0x56),14,Power system status with addtional INA3221 sensor.

:code:`A` - LSM303AGR eCompass data
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This block represents data from the integrated magnetometer and accelerometer in the LSM303AGR eCompass sensor.

The LSM303 block is represented by :py:class:`cryodecoder.blocks.Block_A_LSM303`.

.. autoclass:: cryodecoder.blocks.Block_A_LSM303

.. csv-table::
    :header: Length (bytes),Description,Example
    :widths: auto

    1,Block indentifier,'A'
    1,Block length,12
    2,Magnetometer X,"-32,768 to 32,767"
    2,Magnetometer Y,"-32,768 to 32,767"
    2,Magnetometer Z,"-32,768 to 32,767"
    2,Accelerometer X,"-32,768 to 32,767"
    2,Accelerometer Y,"-32,768 to 32,767"
    2,Accelerometer Z,"-32,768 to 32,767"

.. note::

    TODO: Add reference to conversion formulas or methodology.

:code:`B` - BMA accelerometer data
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This block represents data from the BMA400 accelerometer used on the datalogger receiver board.

The BMA400 block is represented by :py:class:`cryodecoder.blocks.Block_B_BMA400`.
    
.. csv-table::
    :header: Length (bytes),Description,Example
    :widths: auto

    1,Block indentifier,'A'
    1,Block length,6
    2,Accelerometer X,"-32,768 to 32,767"
    2,Accelerometer Y,"-32,768 to 32,767"
    2,Accelerometer Z,"-32,768 to 32,767"

:code:`C` - EC, Temp. and Battery
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This is a common block across many - if not all - CHIL instruments to report electrical conductivity and temperature measurements. It also includes auxiliary data which describe the order of measurement and local battery voltage.

The CHIL block is represented by :py:class:`cryodecoder.blocks.Block_C_CHIL`.

.. csv-table::
    :header: Length (bytes),Description,Value or example
    :widths: auto

    1,Block indentifier,'C'
    1,Block length,7
    1,Sequence number,0 to 255
    2,Battery voltage,3890
    2,EC sensor,0 to 4095
    2,TMP117,3200 (equivalent to 25 deg C)

.. note::

    TODO: Add reference to conversion formulas.

:code:`E` - Receiver environmental data
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This block reports data from the environmental sensors integrated with the CHIL datalogger.

The environmental data block is represented by :py:class:`cryodecoder.blocks.Block_E_Environmental`.

.. csv-table::
    :header: Length (bytes),Description,Example
    :widths: auto

    1,Block indentifier,'E'
    1,Block length,8
    4,Barometric pressure from MS5607,IEEE 754 float
    4,PCB temperature from MS5607,IEEE 754 float

If an SHT30 sensor is available, the length of the block is modified and the temperature and relative humidity are reported in addition to the values from the onboard MS5607 sensor.

.. csv-table::
    :header: Length (bytes),Description,Example
    :widths: auto
    1,Block indentifier,'E'
    1,Block length,12
    4,Barometric pressure from MS5607,IEEE 754 float
    4,PCB temperature from MS5607,IEEE 754 float
    2,External temperature from SHT30,"0 to 65,535"
    2,Relative humidity from SHT30,"0 to 65,535"

.. note::

    TODO: Add reference to conversion formulas.

:code:`K` - Keller pressure sensor
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This block describes data from the Keller 4LD, 7LD and 7LHPD pressure sensors. As well as pressure, the block reports the temperature from the pressure sensor and the scaling values used to convert the digitised readings to physical values.

The Keller pressure sensor block is represented by :py:class:`cryodecoder.blocks.Block_K_Keller`.

.. csv-table::
    :header: Length (bytes),Description,Example
    :widths: auto

    1,Block indentifier,'P'
    1,Block length,13
    2,Pressure sensor value,16,384 to 49,152
    2,Temperature sensor value,16,384 to 49,152
    1,Date of manufacture and sensor type,0111 0100
    4,Pressure min. scaling,IEEE 754 float
    4,Pressure max. scaling,IEEE 754 float

.. note::

    TODO: Add reference to conversion and decoding formulas.

:code:`T` - CTi TILT-05 tilt sensor
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This block reports data from the CTi TILT-05 tilt sensor.

The CTi TILT-05 block is represented by :py:class:`cryodecoder.blocks.Block_T_Tilt`.

.. csv-table::
    :header: Length (bytes),Description,Example
    :widths: auto

    1,Block indentifier,'T'
    1,Block length,10
    2,Accelerometer X,-2,000 to 2,000
    2,Accelerometer Y,-2,000 to 2,000
    2,Accelerometer Z,-2,000 to 2,000
    2,Pitch,-1800 to 1800
    2,Roll,-1800 to 1800

Accelerometer X, Y and Z are reported in units of mg. Pitch and roll are reported in units of one tenth of a degree.

:code:`V` - Datalogger voltage status
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This block reports the battery voltage using the voltage divider interface.

The datalogger voltage block is represented by :py:class:`cryodecoder.blocks.Block_V_Voltage`.

.. csv-table::
    :header: Length (bytes),Description,Example
    :widths: auto
    1,Block indentifier,'V'
    1,Block length,2
    2,Battery voltage divider ADC value,"0 to 65,535"

If present and enabled, it can report the power system status using an INA3221 current and bus monitor.

.. cst-table::
    :header: Length (bytes),Description,Example
    :widths: auto
    1,Block indentifier,'V'
    1,Block length,14
    2,Battery voltage divider ADC value,"0 to 65,535"
    2,Channel 1 shunt voltage,"-32,768 to 32,767"
    2,Channel 1 bus voltage,"-32,768 to 32,767"
    2,Channel 2 shunt voltage,"-32,768 to 32,767"
    2,Channel 2 bus voltage,"-32,768 to 32,767"
    2,Channel 3 shunt voltage,"-32,768 to 32,767"
    2,Channel 3 bus voltage,"-32,768 to 32,767"

LSB values of the shunt and bus voltages are 40 micro Volts.