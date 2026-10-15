"""
This module provides the framework for defining blocks 
as used in CHIL instruments, reading them from byte strings and converting interpreted values back to byte strings. More information on the blocks can be found :doc:`here </blocks/blocks>`.

Blocks
======
Blocks correspond to the :doc:`Level 1 </blocks/level1>`, :doc:`Level 2 </blocks/level2>` or :doc:`Level 3 </blocks/level3>` data structures as defined by the 2026 CHIL instrument protocol. To ensure backwards compatability with the pre-2026 receiver packet formats, two formats of legacy block (:py:class:`Block_C_Cryoegg` and :py:class:`Block_W_Wurst`) are defined.

Each block class extends the :py:class:`Block` abstract base class and is made up of a header (:py:class:`BlockHeader`) which describes the block type and length, and a number of fields (:py:class:`Field`) which contain the data within the block.

The :py:mod:`cryodecoder.blocks` module uses class definitions to describe the various blocks which make up the packet protocol.

Fields
======
Each block definition contains a number of fields which are used to represent the binary encoding of data from the CHIL instruments. The :py:class:`Field` objects is used to convert binary data to interpreted values (i.e. byte array to 16-bit signed integer), and vice versa (16-bit signed integer to byte array).
"""

import cryodecoder
import cryodecoder.exceptions

import copy
from abc import ABC, abstractmethod
from enum import Enum
import struct
from typing import Generic, TypeVar, Union, Literal, Optional
ValueType = TypeVar('ValueType')

##############################################################################
# Fields
##############################################################################
class Field(ABC, Generic[ValueType]):
    """Field defines a generic class which takes raw values in bytes and 
    provides an interface to convert the byte stream into an interpreted value.

    Field exposes .raw and .value properties which provide real-time conversion
    between byte and interpreted values (i.e. byte to float, byte to int).
    """

    def __init__(self, field_order, byte_width = 0, value_default = None):
        """
        :param field_order: order in which the field appears in a block (zero-index)
        :param byte_width: width of the field in bytes
        :param value_default: default value of the field when initialised
        """
        self.field_order = field_order
        self.byte_width = byte_width
        self._raw : bytes = b'\x00' * byte_width
        self._value : Optional[ValueType] = value_default
        self._parent = None

    def __set_name__(self, owner, name):
        self.field_name = name

    @abstractmethod
    def from_bytes(self, bytes):
        """
        derive the interpreted value of the field from byte(s)
        
        :param bytes: the bytes to be converted to an interpreted value
        """
        ...
    @abstractmethod
    def to_bytes(self, value) -> bytes:
        """
        derive the byte representation of the interpreted value

        :param value: the interpreted value to be converted to bytes 
        :returns: the value encoded in a byte string
        :rtype: bytes
        """
        ...

    def __repr__(self):
        return f"{self.field_name}({type(self).__name__}:{self.byte_width} bytes) = {self.value}"

    @property
    def raw(self):
        """
        :returns: the binary representation of the field
        :rtype: bytes
        """
        return self._raw
    @raw.setter
    def raw(self, value : bytes):
        if not isinstance(value, bytes):
            raise TypeError("raw should be of type bytes")
        if len(value) > self.byte_width:
            raise ValueError(f"len(raw) should be <= {self.byte_width}")
        self._raw = value
        self._value = self.from_bytes(value)

    @property
    def value(self):
        """
        :returns: the interpreted value of the field
        """
        return self._value
    @value.setter
    def value(self, value : ValueType):
        self._value = value
        self._raw = self.to_bytes(value) or b''

class Payload(Field):
    """
    Represents a 'special' field which allows for lower-level blocks to be 
    embedded in the middle of the current block (i.e. the higher level MBus 
    RSSI byte is appended after the 'payload' block).
    """

    def __init__(self, field_order):
        super().__init__(field_order, byte_width = 0)

    # Make no conversion between bytes - this is the only form of valid payload
    def from_bytes(self, value):
        return value
    def to_bytes (self, value):
        return value
    
    # Override the original raw method to disable access
    @Field.raw.setter
    def raw(self, value : bytes):
        """
        :raises cryodecoder.exceptions.PayloadAccessError: if the raw value of the payload is attempted the be set, since the payload is only a placeholder field.
        """
        raise cryodecoder.exceptions.PayloadAccessError

    # Override the original value method to disable access
    @Field.value.setter
    def value(self, value : bytes):
        """
        :raises cryodecoder.exceptions.PayloadAccessError: if the value of the payload is attempted the be set, since the payload is only a placeholder field.
        """
        raise cryodecoder.exceptions.PayloadAccessError

class UnsignedIntField(Field[int]):
    """
    Represents a variable-width unsigned integer in binary and interpreted form.
    """

    def __init__(self, field_order : int, byte_width : int, byte_order : Literal["little", "big"] = "little"):
        """
        :param field_order: zero-index order within the block at which this field occurs
        :type field_order: int
        :param byte_width: number of bytes occupied by the integer
        :type byte_width: int
        :param byte_order: endianness of the binary representation ("*little*" or "*big*")
        :type byte_order: str
        """
        super().__init__(field_order, byte_width=byte_width, value_default=0)
        if byte_order not in ("little", "big"):
            raise ValueError(f"Invalid byte_order for field {self.field_name}.")
        self.byte_order = byte_order

    def to_bytes(self, value) -> bytes:
        """
        converts the unsigned integer to its binary representation
        """
        return int.to_bytes(value, self.byte_width, byteorder=self.byte_order)
    def from_bytes(self, value) -> int:
        """
        converts a byte string to an unsigned integer
        """
        return int.from_bytes(value, byteorder=self.byte_order)
    
class SignedIntField(Field[int]):
    """
    Represents a variable-width signed integer in binary and interpreted form.
    """

    def __init__(self, field_order : int, byte_width : int, byte_order : Literal["little", "big"] = "little"):
        """
        :param field_order: zero-index order within the block at which this field occurs
        :type field_order: int
        :param byte_width: number of bytes occupied by the integer
        :type byte_width: int
        :param byte_order: endianness of the binary representation ("*little*" or "*big*")
        :type byte_order: str
        """
        super().__init__(field_order, byte_width=byte_width, value_default=0)
        self.byte_order = byte_order

    def to_bytes(self, value):
        """
        converts the signed integer to its binary representation
        """
        return int.to_bytes(value, self.byte_width, byteorder=self.byte_order, signed=True)
    def from_bytes(self, value):
        """
        converts a byte string to an signed integer
        """
        return int.from_bytes(value, byteorder=self.byte_order, signed=True)
    
class IEEE754Float(Field[float]):
    """
    Represents a 4-byte `IEEE 754`_ floating point number in binary and interpeted 
    form. 

    .. _IEEE 754: https://en.wikipedia.org/wiki/IEEE_754
    """

    def __init__(self, field_order):
        """
        :param field_order: zero-index order within the block at which this field occurs
        :type field_order: int
        """
        super().__init__(field_order, byte_width=4, value_default=0)

    def to_bytes(self, value) -> bytes:
        """
        converts a floating point number to its IEEE 754 floating point representation
        """
        return struct.pack("<f", value)
    
    def from_bytes(self, value) -> float:
        """
        converts a byte string to floating point number
        :rtype: float
        """
        return struct.unpack("<f", value)[0]
    
#-----------------------------------------------------------------------------
# Specific field types
#-----------------------------------------------------------------------------
class TemperatureTMP117Field(SignedIntField):
    """
    Reported temperature from a `TMP117`_ digital temperature sensor.

    .. _TMP117: https://www.ti.com/lit/ds/symlink/tmp117.pdf?
    """

    @property
    def convertedValue(self):
        """
        :return: the reported temperature value in degrees Celsius.
        :rtype: float
        """
        return self._value / 128
    
    @convertedValue.setter
    def convertedValue(self, temperatureValue : float):
        self._value = int(temperatureValue * 128)
        self._raw = self.to_bytes(self._value)

class TemperatureSHT30Field(UnsignedIntField):
    """
    Reported temperature from an `SHT30`_ temperature and humidity probe.
    """

    @property
    def convertedValue(self):
        """
        :return: the reported temperature value in degrees Celsius.
        :rtype: float
        """
        return -45 + 175 * (self._value)/(2**16-1)
    
    @convertedValue.setter
    def convertedValue(self, temperatureValue : float):
        rawValue = (temperatureValue + 45) * (2**16 - 1) / 175
        self._value = rawValue
        self._raw = self.to_bytes(self._value)

class RelativeHumiditySHT30Field(UnsignedIntField):
    """
    Reported relative humidity from an `SHT30`_ temperature and humidity probe.
    """

    @property
    def convertedValue(self):
        """
        :return: the reported relative humidity (as a percentage).
        :rtype: float
        """
        return 100 * (self._value)/(2**16-1)
    
    @convertedValue.setter
    def convertedValue(self, temperatureValue : float):
        rawValue = temperatureValue * (2**16 - 1) / 100
        self._value = rawValue
        self._raw = self.to_bytes(self._value)

class TemperatureKellerField(UnsignedIntField):
    """
    Reported temperature from an `Keller 7L(HP)D`_ pressure sensor.
    
    .. _Keller 7L(HP)D: https://keller-pressure.com/en/products/pressure-transmitters/oem-pressure-transmitters/series-7ld
    """

    @property
    def convertedValue(self):
        """
        :return: the reported temperature value in degrees Celsius.
        :rtype: float
        """
        return ((self._value / 16) - 24) * 0.05 - 50.0
    
    @convertedValue.setter
    def convertedValue(self, temperatureValue : float):
        raise NotImplementedError

class PressureKellerField(UnsignedIntField):
    """
    Reported pressure in bar from an `Keller 7L(HP)D`_ pressure sensor.
    
    .. _Keller 7L(HP)D: https://keller-pressure.com/en/products/pressure-transmitters/oem-pressure-transmitters/series-7ld
    """

    @property
    def convertedValue(self):
        """
        :return: the reported pressure value in bar.
        :rtype: float
        """
        return (self.value - 16384) / 32768 * (self._parent.pressure_max.value - self._parent.pressure_min.value) + 1 # Invalid for now, adjust using date code
    
    @convertedValue.setter
    def convertedValue(self, temperatureValue : float):
        raise NotImplementedError

##############################################################################
# Blocks
##############################################################################
class BlockHeader: # L1(BlockHeader):
    """
    Base class for the header section of CHIL blocks.
    """

    length_byte_width : int = 1
    def to_bytes(self, block) -> bytes:
        """
        :param block: parent block of the BlockHeader to be used in calculating total block length
        :type block: :py:class:`Block`

        :returns: byte representation of the header
        :rtype: bytes"""
        # Calculate length
        length = block.calculate_block_length()
        # Return header
        return block.identifier + \
            int.to_bytes(length, self.length_byte_width, byteorder="little")

    def length(self) -> int:
        """
        :returns: length of the header in bytes
        :rtype: int
        """
        return self.length_byte_width + 1
    
class BlockHeaderL3(BlockHeader):
    length_byte_width : int = 2

class BlockHeaderLegacy(BlockHeader):
    def __init__(self):
        super().__init__()

    def length(self):
        # Define fixed length for legacy headers (W1, W2, C1, C2)
        return 2

    def get_bytes_remaining(self, identifier, classifier):
        if identifier == b'W':
            if classifier == b'1' or classifier == b'\x00':
                return 52
            elif classifier == b'2':
                return 58
            else:
                raise ValueError(f"Invalid legacy packet classifier {identifier}_{classifier}_.")
        elif identifier == b'C':
            if classifier == b'0':
                return 23
            if classifier == b'1':
                return 38
            else:
                raise ValueError(f"Invalid legacy packet classifier {identifier}_{classifier}_.")


# class BlockHeaderL2():
#     pass

class BlockLevel(Enum):
    L1 = 1
    L2 = 2
    L3 = 3
    def __le__(self, v):
        if not isinstance(v, BlockLevel):
            return False
        return self.value <= v.value
    def __ge__(self, v):
        if not isinstance(v, BlockLevel):
            return False
        return self.value >= v.value
    def __gt__(self, v):
        if not isinstance(v, BlockLevel):
            return False
        return self.value > v.value
    def __lt__(self, v):
        if not isinstance(v, BlockLevel):
            return False
        return self.value < v.value
    def __eq__(self, v):
        if not isinstance(v, BlockLevel):
            return False
        return self.value == v.value

class Block(ABC):
    """
    An abstract base class for defining different block types. 
    """

    # Use an abstract class as the default header to ensure override
    header_class = BlockHeader

    # Block level corresponds to Data, Origin or Context (L1, L2 or L3) blocks
    level : BlockLevel = BlockLevel.L1 # defaulting to L1

    def __init__(self, **kwargs):
        # Create array to store fields temporarily
        fields = []
        field_orders = []
        # Iterate through the class fields and create local copies
        for attr in dir(self):
            attr_class = getattr(self, attr).__class__
            if issubclass(attr_class, Field):
                field = getattr(self, attr)
                if field.field_order in field_orders:
                    raise ValueError(f"Invalid field_order in {__class__}")
                new_field = copy.deepcopy(field)
                new_field._parent = self
                setattr(self, attr, new_field)
                fields.append(new_field)
                field_orders.append(new_field.field_order)
        # Sort the fields by field order
        fields.sort(key=lambda x : x.field_order)
        self.fields = tuple(fields)

        # We've assigned our fields, so now check the kwargs for init
        for field in self.fields:
            if field.field_name in kwargs:
                if isinstance(kwargs[field.field_name], bytes):
                    getattr(self, field.field_name).raw = kwargs[field.field_name]
                else:
                    getattr(self, field.field_name).value = kwargs[field.field_name]

        # Initiailise header
        self.header = self.header_class()

    def __len__(self) -> int:
        return self.header.length() + self.count_field_bytes()

    def to_bytes(self) -> bytes:
        field_bytes = b''
        for field in self.fields:
            field_bytes += field.raw
        return self.header.to_bytes(self) + field_bytes
        
    def count_field_bytes(self) -> int:
        length = 0
        for field in self.fields:
            length += field.byte_width
        return length
    
    def __repr_header__(self):
        header = f"Block {type(self).__name__}"
        return header
    
    def __repr_fields__(self):
        """return a human readable representation of the class fields"""
        fields = ""
        for field in self.fields:
            fields += "    " + repr(field) + "\n"
        return fields
    
    def __repr__(self):
        return self.__repr_header__() + ":\n" + self.__repr_fields__()
    
    def calculate_block_length(self) -> int:
        # Start wiht the field bytes
        block_length = self.count_field_bytes()
        # Check whether we have a L2/L3 block
        if isinstance(self, BlockChildren):
            # then iterate through children
            for child in self.children:
                if isinstance(child, BlockChildren):
                    # Only valid for two levels of iteration
                    for grandchild in child.children:
                        block_length += len(grandchild)
                block_length += len(child)
        # return the final count
        return block_length

class BlockChildren(Block):
    """Adds an interface for associating sub-blocks within this block which 
    is used to implement L2 and L3 blocks (Origin and Context) 
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.children = []

    def add_child(self, block):
        if block.level >= self.level:
            raise cryodecoder.exceptions.InvalidNestedBlockError
        else:
            self.children.append(block)
    
    def count_payload_bytes(self) -> int:
        length = 0
        for field in self.fields:
            if isinstance(field, Payload):
                length += len(field._raw)
        return length

    def hasChild(self, type : type) -> bool:
        for child in self.children:
            if isinstance(child, type):
                return True
        return False
    
    def getChild(self, block_type : Union[type, tuple[type]]) -> Optional[Block]: 
        """
        returns the child block of type ``block_type``, if it exists, used for extracting L2 and L1 blocks from their parents.

        :param Union[type, tuple[type]] block_type: type (or tuple of types) of blocks to extract.
        :returns: if it exists, a block of type `block_type`.
        :rtype: :py:class:`Block` or `None`
        """
        for child in self.children:
            if isinstance(child, block_type):
                return child
        return None

    def __len__(self):
        # Add length for all children
        child_length = sum([len(child) for child in self.children])
        return super().__len__() + self.count_payload_bytes() + child_length
    
    def to_bytes(self) -> bytes:
        field_bytes = b''
        for field in self.fields:
            if isinstance(field, Payload):
                for child in self.children:
                    field_bytes += child.to_bytes()
            else:
                field_bytes += field.raw

        return self.header.to_bytes(self) + field_bytes
    
    def __repr_fields__(self):
        """return a human readable representation of the class fields
        accounting for payloads"""
        fields = ""
        payload_field = None
        for field in self.fields:
            if not isinstance(field, Payload):
                fields += "  " + repr(field) + "\n"
            else:
                payload_field = field
        
        payload = ""
        if payload_field is not None:
            payload += "Payload of ["
            if len(self.children):
                payloads = []
                for child in self.children:
                    payloads.append(child.__repr_header__())
                payload += ", ".join(payloads)
            else:
                payload += "no payload"
            payload += "]"

        return fields + payload
        
        

###############################################################################
# BLOCK DEFINITIONS
###############################################################################
class Block_A_LSM303(Block):
    """
    Stores magnetometer and accelerometer data from the `LSM303AGR`_ 
    sensor used in CHIL instrumentation. More details on the LSM303 block format are available :ref:`here <block_a_lsm303>`.

    Magnetometer data are signed 16-bit values which have a code range from -32,768 to 32,767 corresponding to sensor values of ±50 Gauss.

    Accelerometer data are signed 16-bit values which have a code range from -32,768 to 32,767 corresponding to sensor values of ±2g (19.61 m/s\\ :sup:`2`).
    
    :example: Converting magnetometer data to physical values:

        .. code-block:: python

            # Load an LSM303 dataset
            block = Block_A_LSM303(...)

            # Convert the magnetometer sensor to its physical value in Gauss
            mag_x_gauss = 50 * block.mag_x.value / 32768
    
    :example: Converting accelerometer data to physical values:

        .. code-block:: python

            # Load an LSM303 dataset
            block = Block_A_LSM303(...)

            # Convert the acceleration sensor to its physical value in g
            acc_x_gauss = 2 * block.acc_x.value / 32768

    .. note::
        **TODO:** Add reference to Cryowurst and Cryoegg for acc/mag vector orientation.

    :param SignedIntField mag_x: x-axis component of the magnetometer sensor.
    :param SignedIntField mag_y: y-axis component of the magnetometer sensor.
    :param SignedIntField mag_z: z-axis component of the magnetometer sensor.
    :param SignedIntField acc_x: x-axis component of the accelerometer sensor.
    :param SignedIntField acc_y: y-axis component of the accelerometer sensor.
    :param SignedIntField acc_z: z-axis component of the accelerometer sensor.

    .. _LSM303AGR: https://www.st.com/en/mems-and-sensors/lsm303agr.html 
    """

    identifier = b'A'
    header_class = BlockHeader
    """:meta private:"""
    mag_x = SignedIntField(field_order=0, byte_width=2)
    mag_y = SignedIntField(field_order=1, byte_width=2)
    mag_z = SignedIntField(field_order=2, byte_width=2)
    acc_x = SignedIntField(field_order=3, byte_width=2)
    acc_y = SignedIntField(field_order=4, byte_width=2)
    acc_z = SignedIntField(field_order=5, byte_width=2)

class Block_B_BMA400(Block):
    """
    Stores accelerometer data from the `BMA400`_ accelerometer used on the CHIL receiver. More details on the BMA400 block format are available :ref:`here <block_b_bma400>`.

    Accelerometer data are signed 12-bit values which have a code range from -2048 to +2047 corresponding to sensor values of ±2g (19.61 m/s\\ :sup:`2`).

    :example: Converting acceleration data to physical values:

        .. code-block:: python

            # Load a BMA400 dataset
            block = Block_B_BMA400(...)

            # Convert the acceleration to its physical value in g (m/s^2)
            acc_x_g = 2 * block.acc_x.value / 2048

    :param SignedIntField acc_x: x-axis component of the accelerometer sensor.
    :param SignedIntField acc_y: y-axis component of the accelerometer sensor.
    :param SignedIntField acc_z: z-axis component of the accelerometer sensor.

    .. _BMA400: https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bma400-ds000.pdf
    """
    identifier = b'B'
    header_class = BlockHeader
    """:meta private:"""
    acc_x = SignedIntField(field_order=0, byte_width=2)
    acc_y = SignedIntField(field_order=1, byte_width=2)
    acc_z = SignedIntField(field_order=2, byte_width=2)
    
class Block_C_CHIL(Block):
    """
    Stores instrument battery voltage, packet metadata, temperature and conductivity measurements. The origin of the temperature measurement can with the instrument type but is typically a `TMP117`_ sensor. More details on the CHIL block format are available :ref:`here <block_c_chil>`.

    :example: Get measured temperature value from the TMP117 sensor.

        .. code-block:: python

            # Load a CHIL sensor dataset
            block = Block_C_CHIL(...)

            # Convert the raw temperature value to degrees celsius.
            temp_raw_to_degC = block.temperature_tmp117.value / 128.0

            # or use the built in .convertedValue to do the same
            assert temp_raw_to_degC == block.temperature_tmp117.convertedValue
    
    :param UnsignedIntField sequence_number: Sequence number of the transmitted packet increments by one after each transmission from 0 to 255 and then resets.
    :param UnsignedIntField voltage_battery: Battery voltage of the instrument in millivolts (mV).
    :param UnsignedIntField conductivity: Uncalibrated conductivity sensor measurement in millivolts (mV). 
    :param TemperatureTMP117Field temperature_tmp117: Raw temperature value from the TMP117 temperature sensor.

    """

    identifier         = b'C'
    header_class       = BlockHeader
    """:meta private:"""
    sequence_number    = UnsignedIntField(field_order=0, byte_width=1)
    voltage_battery    = UnsignedIntField(field_order=1, byte_width=2)
    conductivity       = UnsignedIntField(field_order=2, byte_width=2)
    temperature_tmp117 = TemperatureTMP117Field(field_order=3, byte_width=2)

class Block_E_Environmental(Block):
    """
    Stores the environmental data (temperature, pressure, relative humidity) from the receiver. More details on the environmental block format are available :ref:`here <block_e_environmental>`.

    All dataloggers contain the `MS5607`_ pressure and temperature sensor. There is the option to install an external `SHT30`_ temperature and relative humidity sensor.

    :example: Get measured temperature and pressure values from the MS5607.

        .. code-block:: python

            # Load a receiver environmental sensor dataset
            block = Block_E_Environmental(...)

            # Get the air temperature in degrees celsius.
            temperature = block.temperature_ms5607.value

            # Get the air pressure in bar.
            temperature = block.pressure_ms5607.value

    :example: Get measured temperature and relative humdidity from the SHT30.

        .. code-block:: python

            # Load a receiver environmental sensor dataset
            block = Block_E_Environmental(...)

            # Get the air temperature in degrees celsius.
            temperature = block.temperature_sht30.convertedValue

            # Get the relative humditiy in percent
            # ...requires temperature from SHT30...
            rel_humidity = block.humidity_sht30.convertedValue(
                block.temperature_sht30.value
            )
            
    :param IEEE754Float pressure_ms5607: Surface air pressure recorded by the datalogger in bar.
    :param IEEE754Float temperature_ms5607: Internal air temperature of the datalogger in degrees celsius.
    :param TemperatureSHT30Field temperature_sht30: *(Optional)* External air temperature recorded by the datalogger using an SHT30 sensor.
    :param RelativeHumiditySHT30Field humidity_sht30: *(Optional)* External relative humidity recorded by the datalogger using an SHT30 sensor.

    .. _MS5607: https://www.te.com/en/product-MS560702BA03-50.html
    
    .. _SHT30: https://thepihut.com/products/sht-30-mesh-protected-weather-proof-temperature-humidity-sensor

    """
    
    identifier = b'E'
    header_class = BlockHeader
    """:meta private:"""
    pressure_ms5607    = IEEE754Float(field_order=0)
    temperature_ms5607 = IEEE754Float(field_order=1)
    temperature_sht30  = TemperatureSHT30Field(field_order=2, byte_width=2)
    humidity_sht30     = RelativeHumiditySHT30Field(field_order=3, byte_width=2)

class Block_K_Keller(Block):
    """
    Stores the temperature and pressure data from a Keller `7LD`_ or `7LHPD`_ pressure sensor. More details on the Keller block format are available :ref:`here <block_k_keller>`.

    .. warning::

        If the ``pressure_min`` or ``pressure_max`` are invalid, it can cause the ``pressure.convertedValue`` field to be incorrectly converted. If values from the pressure sensor do not look valid, make sure to check  ``pressure.value``. 

    :example: Read the temperature and pressure from a Keller sensor

        .. code-block:: python

            # Read a Block_K_Keller block
            block = Block_K_Keller(...)

            # Get the temperature value in celsius
            temperature_degC = block.temperature.convertedValue

            # Get the pressure value in bar
            pressure_bar = block.pressure.convertedValue

    :example: Convert raw temperature and pressure values from a Keller sensor, if the minimum and maximum pressure are known

        .. code-block:: python

            # Read a Block_K_Keller block
            block = Block_K_Keller(...)

            # Get the temperature value in celsius
            temperature_degC = (block.temperature.value >> 4) - 24 ) * 0.05 - 50.0

            # Set the known minimum and maximum pressure values assuming it
            # is a seal gauge sensor (zero at 1.0 bar absolute).
            p_min = 0.0  # minimum pressure
            p_max = 30.0 # maximum pressure

            # Get the pressure value in bar
            pressure_bar = (block.pressure.value - 16384) x (p_max - p_min) / 32768

    :param PressureKellerField pressure: measured pressure value.
    :param TemperatureKellerField temperature: measured temperature value.
    :param UnsignedIntField date_code: 
    :param IEEE754Float pressure_min: Minimum rated pressure value (corresponding to a raw value of 16,384)
    :param IEEE754Float pressure_max: Maximum rated pressure value (corresponding to a raw value of 49,152). 
    """
    
    identifier = b'K'
    header_class = BlockHeader
    """:meta private:"""
    pressure = PressureKellerField(field_order=0, byte_width=2)
    temperature = TemperatureKellerField(field_order=1, byte_width=2)
    date_code = UnsignedIntField(field_order=2, byte_width=1)
    pressure_min = IEEE754Float(field_order=3)
    pressure_max = IEEE754Float(field_order=4)

class Block_V_Voltage(Block):
    """
    Stores the receiver power system data from the voltage divider input voltage monitor and power sensing `INA3221`_ sensor. More details on the Keller block format are available :ref:`here <block_v_voltage>`.

    .. note::

        The input voltage divider circuit on newer dataloggers appears to have a very non-linear characteristic which requires further investigation.

    Shunt resistors for the INA3321 are 0.1 Ohms, which means that the current flowing through them can be calculated from the shunt voltage divided by resistance.

    The shunt voltage and bus voltage fields from the INA3221 are 13 bits long and left-shifted into a 16-bit field. To convert the raw shunt voltage value to volts, multiply by 5e-6. To convert the raw bus voltage value to volts, multiply by 1e-3.

    :example: Calculate power from solar panel.

        .. code-block::

            # Read a Block_V_Voltage block
            block = Block_V_Voltage(...)

            # Calculate current
            R_shunt = 0.1 # Ohms
            current_ch1_amps = block.voltage_shunt_ch1.value * 5e-6 / R_shunt
            
            # Calculate voltage
            voltage_ch1_volts = block.voltage_bus_ch1.value * 1e-3

            # Calculate power
            power_ch1_watts = current_ch1_amps * voltage_ch1_volts

    :param UnsignedIntField voltage_battery: raw output from the voltage divider input voltage monitor.
    :param UnsignedIntField voltage_shunt_ch1: shunt voltage from the solar panel (channel 1), used to calculate the current.
    :param UnsignedIntField voltage_bus_ch1: bus voltage from the solar panel (channel 1), used to derive total power.
    :param UnsignedIntField voltage_shunt_ch2: shunt voltage from the solar regulator (channel 2), used to calculate the current.
    :param UnsignedIntField voltage_bus_ch2: bus voltage from the solar regulator (channel 3), used to derive total power.
    :param UnsignedIntField voltage_shunt_ch3: shunt voltage to the datalogger (channel 3), used to calculate the current.
    :param UnsignedIntField voltage_bus_ch3: input voltage at the datalogger (channel 3), used to derive total power.

    .. _INA3221: https://www.ti.com/lit/ds/symlink/ina3221.pdf
    """
    
    identifier = b'V'
    header_class = BlockHeader
    """:meta private:"""
    
    voltage_battery   = UnsignedIntField(field_order=0, byte_width=2)
    voltage_shunt_ch1 = UnsignedIntField(field_order=1, byte_width=2)
    voltage_bus_ch1   = UnsignedIntField(field_order=2, byte_width=2)
    voltage_shunt_ch2 = UnsignedIntField(field_order=3, byte_width=2)
    voltage_bus_ch2   = UnsignedIntField(field_order=4, byte_width=2)
    voltage_shunt_ch3 = UnsignedIntField(field_order=5, byte_width=2)
    voltage_bus_ch3   = UnsignedIntField(field_order=6, byte_width=2)

class Block_T_Tilt(Block):
    """
    Stores data from the CTi `TILT-05`_ accelerometer and orientation sensor. More details on the Keller block format are available :ref:`here <block_t_tilt>`. 

    Accelerometer data are signed 16-bit values are return acceleration values in units of milli-g. To convert to g (m\\ :sup:`2`), divide by 1,000.

    :example: Convert pitch and roll to units of degrees

        .. code-block:: python

            # Read a Block_T_Tilt block
            block = Block_T_Tilt(...)

            # Convert pitch and roll to degrees
            pitch_degress = block.pitch_tenth_deg.value / 10
            roll_degrees  = block.roll_tenth_deg.value / 10

    :param SignedIntField acc_x: x-axis component of the accelerometer sensor.
    :param SignedIntField acc_y: y-axis component of the accelerometer sensor.
    :param SignedIntField acc_z: z-axis component of the accelerometer sensor.
    :param SignedIntField pitch_tenth_deg: pitch (angle) along x-axis in tenths of a degree.
    :param SignedIntField roll_tenth_deg: roll (angle) along y-axis in tenths of a degree.

    .. _TILT-05: https://ctisensors.com/Documents/TILT-05-Datasheet.pdf 
    """
    
    identifier = b'T'
    header_class = BlockHeader
    acc_x = SignedIntField(field_order=0, byte_width=2)
    acc_y = SignedIntField(field_order=1, byte_width=2)
    acc_z = SignedIntField(field_order=2, byte_width=2)
    pitch_tenth_deg = UnsignedIntField(field_order=3, byte_width=2)
    roll_tenth_deg  = UnsignedIntField(field_order=4, byte_width=2)

class Block_M_MBusPacket(BlockChildren):
    """
    Mirrors the format of the Radiocrafts UART interface `packet format <https://radiocrafts.com/uploads/MBUS_User_Manual.pdf>`__, acting as a transport layer for the CHIL packet contained within :py:class:`Payload`. More details on the Keller block format are available :ref:`here <block_t_tilt>`.

    The received signal strength (``rssi``) can be converted to units of RSSI by multiplying with -1 and dividing by 2.

    :example: Convert received signal strength to dBm

        .. code-block:: python

            # Read a Block_M_MBus block
            block = Block_M_MBus(...)

            # Convert RSSI to dBm
            rssi_dBm = -block.rssi.value / 2

    :param UnsignedIntField channel_number: channel number (1 or 2) on which the packet was received.
    :param UnsignedIntField c_field: control field in the MBus packet header.
    :param UnsignedIntField m_field: manufacturer field in MBus packet header.
    :param UnsignedIntField uid: unique identifier, used to identify CHIL instruments, i.e. `CE240001` or `CF230010`.
    :param UnsignedIntField version: version field in the MBus packet header.
    :param UnsignedIntField device: device field in the MBus packet header.
    :param UnsignedIntField ci_field: control information field in the MBus packet header, used to discriminate between 2023 and 2026 packet formats.
    :param Payload payload: contents of the MBus packet.
    :param UnsignedIntField rssi: encoded received signal strength.
    """

    identifier     = b'M'
    level          = BlockLevel.L2
    header_class   = BlockHeader
    """:meta private:"""
    channel_number = UnsignedIntField(field_order=0, byte_width=1)
    c_field  = UnsignedIntField(field_order=1, byte_width=1)
    m_field  = UnsignedIntField(field_order=2, byte_width=2, byte_order="big")
    uid      = UnsignedIntField(field_order=3, byte_width=4, byte_order="big")
    version  = UnsignedIntField(field_order=4, byte_width=1)
    device   = UnsignedIntField(field_order=5, byte_width=1)
    ci_field = UnsignedIntField(field_order=6, byte_width=1)
    payload  = Payload(field_order=7)
    rssi     = UnsignedIntField(field_order=8, byte_width=1)

class Block_M_MBusPacketCryoegg2023(BlockChildren):
    """
    To facilitate backwards compatability, when 2026 dataloggers receive a 2023 version packet from Cryoegg, the data is interpreted as a :py:class:`Block_M_MBusPacketCryoegg2023`.

    Conversion of the :py:attr:`pressure` field requires prior knowledge of the minimum and maximum pressure values.
    
    :example: Convert raw temperature and pressure values from a 2023 format Cryoegg packet.

        .. code-block:: python

            # Read a Block_M_MBusPacketCryoegg2023 block
            block = Block_M_MBusPacketCryoegg2023(...)

            # Get the temperature value in celsius
            temperature_degC = (block.temperature_keller.value >> 4) - 24 ) * 0.05 - 50.0

            # Set the known minimum and maximum pressure values assuming it
            # is a seal gauge sensor (zero at 1.0 bar absolute).
            p_min = 0.0  # minimum pressure
            p_max = 30.0 # maximum pressure

            # Get the pressure value in bar
            pressure_bar = (block.pressure.value - 16384) x (p_max - p_min) / 32768

    :param UnsignedIntField channel_number: channel number (0 or 1) on which the packet was received.
    :param UnsignedIntField c_field: control field in the MBus packet header.
    :param UnsignedIntField m_field: manufacturer field in MBus packet header.
    :param UnsignedIntField uid: unique identifier, used to identify CHIL instruments, i.e. `CE240001` or `CF230010`.
    :param UnsignedIntField version: version field in the MBus packet header.
    :param UnsignedIntField device: device field in the MBus packet header.
    :param UnsignedIntField ci_field: control information field in the MBus packet header, used to discriminate between 2023 and 2026 packet formats.
    :param UnsignedIntField conductivity: Uncalibrated conductivity sensor measurement in millivolts (mV). 
    :param SignedIntField temperature_pt1000: Unused value from the PT1000 temperature sensor (deprecated).
    :param PressureKellerField pressure: measured pressure value.
    :param TemperatureKellerField temperature_keller: measured temperature value.
    :param UnsignedIntField voltage_battery: Battery voltage of the instrument in millivolts (mV).
    :param UnsignedIntField sequence_number: Sequence number of the transmitted packet increments by one after each transmission from 0 to 255 and then resets.
    :param UnsignedIntField rssi: encoded received signal strength.
    """
    
    identifier     = b'M'
    level          = BlockLevel.L2
    header_class   = BlockHeader
    """:meta private:"""
    channel_number = UnsignedIntField(field_order=0, byte_width=1)
    c_field  = UnsignedIntField(field_order=1, byte_width=1)
    m_field  = UnsignedIntField(field_order=2, byte_width=2, byte_order="big")
    uid      = UnsignedIntField(field_order=3, byte_width=4, byte_order="big")
    version  = UnsignedIntField(field_order=4, byte_width=1)
    device   = UnsignedIntField(field_order=5, byte_width=1)
    ci_field = UnsignedIntField(field_order=6, byte_width=1)
    # legacy payload start
    conductivity = UnsignedIntField(field_order=7, byte_width=2)
    temperature_pt1000 = SignedIntField(field_order=8, byte_width=2)
    pressure           = UnsignedIntField(field_order=9, byte_width=2)
    temperature_keller = UnsignedIntField(field_order=10, byte_width=2)
    voltage_battery    = UnsignedIntField(field_order=11, byte_width=2)
    sequence_number    = UnsignedIntField(field_order=12, byte_width=1)
    # legacy payload end
    rssi               = UnsignedIntField(field_order=13, byte_width=1)

class Block_M_MBusPacketCryowurst2023(BlockChildren):
    """
    To facilitate backwards compatability, when 2026 dataloggers receive a 2023 version packet from Cryowurst, the data is interpreted as a :py:class:`Block_M_MBusPacketCryowurst2023`.

    Conversion of the :py:attr:`pressure` field requires prior knowledge of the minimum and maximum pressure values.
    
    :example: Convert raw temperature and pressure values from a 2023 format Cryowurst packet.

        .. code-block:: python

            # Read a Block_M_MBusPacketCryowurst2023 block
            block = Block_M_MBusPacketCryowurst2023(...)

            # Get the temperature value in celsius
            temperature_degC = (block.temperature_keller.value >> 4) - 24 ) * 0.05 - 50.0

            # Set the known minimum and maximum pressure values assuming it
            # is a seal gauge sensor (zero at 1.0 bar absolute).
            p_min = 0.0  # minimum pressure
            p_max = 30.0 # maximum pressure

            # Get the pressure value in bar
            pressure_bar = (block.pressure.value - 16384) x (p_max - p_min) / 32768

    :param UnsignedIntField channel_number: channel number (0 or 1) on which the packet was received.
    :param UnsignedIntField c_field: control field in the MBus packet header.
    :param UnsignedIntField m_field: manufacturer field in MBus packet header.
    :param UnsignedIntField uid: unique identifier, used to identify CHIL instruments, i.e. `CE240001` or `CF230010`.
    :param UnsignedIntField version: version field in the MBus packet header.
    :param UnsignedIntField device: device field in the MBus packet header.
    :param UnsignedIntField ci_field: control information field in the MBus packet header, used to discriminate between 2023 and 2026 packet formats.
    :param TemperatureTMP117Field temperature_tmp117: Raw temperature value from the TMP117 temperature sensor.
        :param SignedIntField mag_x: x-axis component of the magnetometer sensor.
    :param SignedIntField mag_y: y-axis component of the magnetometer sensor.
    :param SignedIntField mag_z: z-axis component of the magnetometer sensor.
    :param SignedIntField acc_x: x-axis component of the accelerometer sensor.
    :param SignedIntField acc_y: y-axis component of the accelerometer sensor.
    :param SignedIntField acc_z: z-axis component of the accelerometer sensor.
    :param SignedIntField acc_tilt_x: x-axis component of the TILT-05 accelerometer sensor.
    :param SignedIntField acc_tilt_y: y-axis component of the TILT-05 accelerometer sensor.
    :param SignedIntField acc_tilt_z: z-axis component of the TILT-05 accelerometer sensor.
    :param SignedIntField pitch_tenth_deg: pitch (angle) along x-axis of the TILT-05 sensor in tenths of a degree.
    :param SignedIntField roll_tenth_deg: roll (angle) along y-axis of the TILT-05 sensor in tenths of a degree.
    :param UnsignedIntField conductivity: Uncalibrated conductivity sensor measurement in millivolts (mV).
    :param PressureKellerField pressure: measured pressure value.
    :param TemperatureKellerField temperature_keller: measured temperature value.
    :param UnsignedIntField voltage_battery: Battery voltage of the instrument in millivolts (mV).
    :param UnsignedIntField sequence_number: Sequence number of the transmitted packet increments by one after each transmission from 0 to 255 and then resets.
    :param UnsignedIntField rssi: encoded received signal strength.
    """
    identifier     = b'M'
    level          = BlockLevel.L2
    header_class   = BlockHeader
    """:meta private:"""
    legacy_payload_length = 11 # derived from below
    channel_number = UnsignedIntField(field_order=0, byte_width=1)
    c_field  = UnsignedIntField(field_order=1, byte_width=1)
    m_field  = UnsignedIntField(field_order=2, byte_width=2, byte_order="big")
    uid      = UnsignedIntField(field_order=3, byte_width=4, byte_order="big")
    version  = UnsignedIntField(field_order=4, byte_width=1)
    device   = UnsignedIntField(field_order=5, byte_width=1)
    ci_field = UnsignedIntField(field_order=6, byte_width=1)
    # legacy payload start
    temperature_tmp117 = TemperatureTMP117Field(field_order=7, byte_width=2)
    mag_x = SignedIntField(field_order=8, byte_width=2)
    mag_y = SignedIntField(field_order=9, byte_width=2)
    mag_z = SignedIntField(field_order=10, byte_width=2)
    acc_x = SignedIntField(field_order=11, byte_width=2)
    acc_y = SignedIntField(field_order=12, byte_width=2)
    acc_z = SignedIntField(field_order=13, byte_width=2)
    acc_tilt_x = SignedIntField(field_order=14, byte_width=2)
    acc_tilt_y = SignedIntField(field_order=15, byte_width=2)
    acc_tilt_z = SignedIntField(field_order=16, byte_width=2)
    pitch_tenth_deg = SignedIntField(field_order=17, byte_width=2)
    roll_tenth_deg = SignedIntField(field_order=18, byte_width=2)
    conductivity = UnsignedIntField(field_order=19, byte_width=2)
    pressure = UnsignedIntField(field_order=20, byte_width=2)
    temperature_keller = UnsignedIntField(field_order=21, byte_width=2)
    voltage_battery = UnsignedIntField(field_order=22, byte_width=2)
    sequence_number = UnsignedIntField(field_order=23, byte_width=1)
    # legacy payload end
    rssi               = UnsignedIntField(field_order=24, byte_width=1)

class Block_R_Receiver(BlockChildren):
    """
    Is an intermediate block which encapsulates :doc:`Level 1 blocks <level1>` associated with the receiver.
    """
    identifier     = b'R'
    level          = BlockLevel.L2
    header_class   = BlockHeader
    """:meta private:"""
    payload  = Payload(field_order=0)
    
class Block_D_Datalogger(BlockChildren):
    """
    Stores data associated with reception of a data packet from CHIL instrument.

    .. warning::

        The :py:attr:`timestamp` field may be incorrect if the receiver does not have a valid Iridium connection and has reset since being programmed. 

    .. example: convert the timestamp value to a Python datetime object

        ..code:: python

            # Get datalogger block
            block = BlocK_D_Datalogger(...)

            # Convert timestmap to datetime object
            import datetime.datetime
            timestamp = datetime.datetime.fromtimestamp(block.timestamp.value)

    :param UnsignedIntField receiver_id: identifier associated with the receiver (as a 32-bit numeric value or 4-byte ASCII string).
    :param UnsignedIntField timestamp: time at which the packet was received as a Unix timestamp (seconds since 1970-01-01 00:00:00).
    :param UnsignedIntField sequence_number: Not currently implemented. Sequence number of the received packet, increments by one after each reception from 0 to 255 and then resets.
    :param Payload payload: stores the received packet.
    """
    identifier = b'D'
    level = BlockLevel.L3
    header_class = BlockHeaderL3
    """:meta private:"""
    receiver_id     = UnsignedIntField(field_order=0, byte_width=4)
    timestamp       = UnsignedIntField(field_order=1, byte_width=4)
    sequence_number = UnsignedIntField(field_order=2, byte_width=1)
    payload         = Payload(field_order=3)
    
class Block_H_Housekeeping(BlockChildren):
    """
    Otherwise identical to :py:class:`Block_D_Datalogger`, the housekeeping block is intended to be used for storage and transmission of 'housekeeping' data associated with the receiver (i.e. not data packets).

    .. warning::

        The :py:attr:`timestamp` field may be incorrect if the receiver does not have a valid Iridium connection and has reset since being programmed. 

    .. example: convert the timestamp value to a Python datetime object

        ..code:: python

            # Get datalogger block
            block = BlocK_D_Datalogger(...)

            # Convert timestmap to datetime object
            import datetime.datetime
            timestamp = datetime.datetime.fromtimestamp(block.timestamp.value)

    :param UnsignedIntField receiver_id: identifier associated with the receiver (as a 32-bit numeric value or 4-byte ASCII string).
    :param UnsignedIntField timestamp: time at which the packet was received as a Unix timestamp (seconds since 1970-01-01 00:00:00).
    :param UnsignedIntField sequence_number: Not currently implemented. Sequence number of the received packet, increments by one after each reception from 0 to 255 and then resets.
    :param Payload payload: stores the received packet.
    """
    identifier = b'H'
    level = BlockLevel.L3
    header_class = BlockHeaderL3
    """:meta private:"""
    receiver_id     = UnsignedIntField(field_order=0, byte_width=4)
    timestamp       = UnsignedIntField(field_order=1, byte_width=4)
    sequence_number = UnsignedIntField(field_order=2, byte_width=1)
    payload         = Payload(field_order=3)

class Block_C_Cryoegg(Block):
    """
    Represents a Cryoegg packet transmitted by a 2023 version of the CHIL datalogger.

    The :py:class:`Block_C_Cryoegg` combines properties which are distributed across Level 1, 2 and 3 blocks in the new format. It contains measured values from the environmental sensors in the receiver in addition to the reported Cryoegg data. 2023 version Cryoegg instruments do not have accelerometers installed so this information is not available.

    .. note::

        See :py:class:`Block_M_MBusPacket` for hints on interpreting the MBus parameters:
        
        * ``c_field``, ``m_field``, ``uid``, ``version``, ``device``, ``ci_field`` and ``rssi``. 

        See :py:class:`Block_M_MBusPacketCryoegg2023` for hints on interpreting the 2023 Cryoegg parameters:

        * ``conductivity``, ``pressure``, ``temperature_keller``, ``battery_voltage`` and ``sequence_number``.
    
    :example: convert ``logger_voltage`` to a value in Volts

        .. code-block:: python

            # Load a Block_C_Cryoegg
            block = Block_C_Cryoegg(...)

            # Convert the raw logger voltage using a first-order polynomial
            # V = m * raw + c
            m = 0.0187
            c = - 27.713 
            battery_voltage_V = m * block.logger_voltage.value + c

    :param UnsignedIntField timestamp: time at which the packet was received as a Unix timestamp (seconds since 1970-01-01 00:00:00).
    :param IEEE754Float logger_pressure: Surface air pressure recorded by the datalogger in bar.
    :param IEEE754Float logger_temperature: Internal air temperature of the datalogger in degrees celsius.
    :param UnsignedIntField logger_voltage: Raw value representing the battery voltage at the receiver.
    :param UnsignedIntField channel_number: The radio channel number (1 or 2) on which the packet was received.
    :param UnsignedIntField length: The length of the MBus packet that follows this byte.
    :param UnsignedIntField c_field: control field in the MBus packet header.
    :param UnsignedIntField m_field: manufacturer field in MBus packet header.
    :param UnsignedIntField uid: unique identifier, used to identify CHIL instruments, i.e. `CE240001` or `CF230010`.
    :param UnsignedIntField version: version field in the MBus packet header.
    :param UnsignedIntField device: device field in the MBus packet header.
    :param UnsignedIntField ci_field: control information field in the MBus packet header, used to discriminate between 2023 and 2026 packet formats.
    :param UnsignedIntField conductivity: Uncalibrated conductivity sensor measurement in millivolts (mV). 
    :param SignedIntField temperature_pt1000: Unused value from the PT1000 temperature sensor (deprecated).
    :param PressureKellerField pressure: measured pressure value.
    :param TemperatureKellerField temperature_keller: measured temperature value.
    :param UnsignedIntField voltage_battery: Battery voltage of the instrument in millivolts (mV).
    :param UnsignedIntField sequence_number: Sequence number of the transmitted packet increments by one after each transmission from 0 to 255 and then resets.
    :param UnsignedIntField rssi: encoded received signal strength.
    """

    identifier = b'C'
    level = BlockLevel.L1
    header_class = BlockHeaderLegacy
    """:meta private:"""
    # -----------------------------------------------------------------
    # Fields:
    # -----------------------------------------------------------------
    timestamp           = UnsignedIntField(field_order=0, byte_width=4)
    logger_temperature  = IEEE754Float(field_order=1)
    logger_pressure     = IEEE754Float(field_order=2)
    logger_voltage      = UnsignedIntField(field_order=3, byte_width=2)
    channel_number      = UnsignedIntField(field_order=4, byte_width=1)
    length              = UnsignedIntField(field_order=5, byte_width=1)
    c_field             = UnsignedIntField(field_order=6, byte_width=1)
    m_field             = UnsignedIntField(field_order=7, byte_width=2, byte_order="big")
    uid                 = UnsignedIntField(field_order=8, byte_width=4, byte_order="big")
    version             = UnsignedIntField(field_order=9, byte_width=1)
    device              = UnsignedIntField(field_order=10, byte_width=1)
    ci_field            = UnsignedIntField(field_order=11, byte_width=1)
    # legacy payload start ---------------------------------------------
    conductivity        = UnsignedIntField(field_order=12, byte_width=2)
    temperature_pt1000  = UnsignedIntField(field_order=13, byte_width=2)
    pressure            = UnsignedIntField(field_order=14, byte_width=2)
    temperature_keller  = UnsignedIntField(field_order=15, byte_width=2)
    battery_voltage     = UnsignedIntField(field_order=16, byte_width=2)
    sequence_number     = UnsignedIntField(field_order=17, byte_width=1)
    # legacy payload end -----------------------------------------------
    rssi                = UnsignedIntField(field_order=18, byte_width=1)

class Block_W_Wurst(Block):
    """
    Represents a Cryowurst packet transmitted by a 2023 version of the CHIL datalogger.

    The :py:class:`Block_W_Wurst` combines properties which are distributed across Level 1, 2 and 3 blocks in the new format. It contains measured values from the environmental sensors in the receiver in addition to the reported Cyrowurst data. 2023 version Cyrowurst instruments do not have accelerometers installed so this information is not available.

    .. note::

        See :py:class:`Block_M_MBusPacket` for hints on interpreting the MBus parameters:
        
        * ``c_field``, ``m_field``, ``uid``, ``version``, ``device``, ``ci_field`` and ``rssi``.

        See :py:class:`Block_M_MBusPacketCryowurst2023` for hints on interpreting the 2023 Cyrowurst parameters:
        
        * ``mag_``, ``acc_``, ``acc_tilt_``, ``pitch_tenth_deg``, ``roll_tenth_deg``, ``conductivity``, ``pressure``, ``temperature_keller``, ``battery_voltage`` and ``sequence_number``.
    
    :example: convert ``logger_voltage`` to a value in Volts

        .. code-block:: python

            # Load a Block_C_Cryoegg
            block = Block_C_Cryoegg(...)

            # Convert the raw logger voltage using a first-order polynomial
            # V = m * raw + c
            m = 0.0187
            c = - 27.713 
            battery_voltage_V = m * block.logger_voltage.value + c
    
    :param UnsignedIntField timestamp: time at which the packet was received as a Unix timestamp (seconds since 1970-01-01 00:00:00).
    :param IEEE754Float logger_pressure: Surface air pressure recorded by the datalogger in bar.
    :param IEEE754Float logger_temperature: Internal air temperature of the datalogger in degrees celsius.
    :param UnsignedIntField logger_voltage: Raw value representing the battery voltage at the receiver.
    :param UnsignedIntField channel_number: The radio channel number (1 or 2) on which the packet was received.
    :param UnsignedIntField length: The length of the MBus packet that follows this byte.
    :param UnsignedIntField c_field: control field in the MBus packet header.
    :param UnsignedIntField m_field: manufacturer field in MBus packet header.
    :param UnsignedIntField uid: unique identifier, used to identify CHIL instruments, i.e. `CE240001` or `CF230010`.
    :param UnsignedIntField version: version field in the MBus packet header.
    :param UnsignedIntField device: device field in the MBus packet header.
    :param UnsignedIntField ci_field: control information field in the MBus packet header, used to discriminate between 2023 and 2026 packet formats.
    :param UnsignedIntField conductivity: Uncalibrated conductivity sensor measurement in millivolts (mV). 
    :param SignedIntField temperature_pt1000: Unused value from the PT1000 temperature sensor (deprecated).
    :param PressureKellerField pressure: measured pressure value.
    :param TemperatureKellerField temperature_keller: measured temperature value.
    :param UnsignedIntField voltage_battery: Battery voltage of the instrument in millivolts (mV).
    :param UnsignedIntField sequence_number: Sequence number of the transmitted packet increments by one after each transmission from 0 to 255 and then resets.
    :param TemperatureTMP117Field temperature_tmp117: Raw temperature value from the TMP117 temperature sensor.
    :param SignedIntField mag_x: x-axis component of the magnetometer sensor.
    :param SignedIntField mag_y: y-axis component of the magnetometer sensor.
    :param SignedIntField mag_z: z-axis component of the magnetometer sensor.
    :param SignedIntField acc_x: x-axis component of the accelerometer sensor.
    :param SignedIntField acc_y: y-axis component of the accelerometer sensor.
    :param SignedIntField acc_z: z-axis component of the accelerometer sensor.
    :param SignedIntField acc_tilt_x: x-axis component of the TILT-05 accelerometer sensor.
    :param SignedIntField acc_tilt_y: y-axis component of the TILT-05 accelerometer sensor.
    :param SignedIntField acc_tilt_z: z-axis component of the TILT-05 accelerometer sensor.
    :param SignedIntField pitch_tenth_deg: pitch (angle) along x-axis of the TILT-05 sensor in tenths of a degree.
    :param SignedIntField roll_tenth_deg: roll (angle) along y-axis of the TILT-05 sensor in tenths of a degree.
    :param UnsignedIntField conductivity: Uncalibrated conductivity sensor measurement in millivolts (mV).
    :param PressureKellerField pressure: measured pressure value.
    :param TemperatureKellerField temperature_keller: measured temperature value.
    :param UnsignedIntField voltage_battery: Battery voltage of the instrument in millivolts (mV).
    :param UnsignedIntField sequence_number: Sequence number of the transmitted packet increments by one after each transmission from 0 to 255 and then resets.
    :param UnsignedIntField rssi: encoded received signal strength.
    """
    
    identifier = b'W'
    level = BlockLevel.L1
    header_class = BlockHeaderLegacy
    """:meta private:"""
    # -----------------------------------------------------------------
    # Fields:
    # -----------------------------------------------------------------
    timestamp           = UnsignedIntField(field_order=0, byte_width=4)
    logger_temperature  = IEEE754Float(field_order=1)
    logger_pressure     = IEEE754Float(field_order=2)
    logger_voltage      = UnsignedIntField(field_order=3, byte_width=2)
    channel_number      = UnsignedIntField(field_order=4, byte_width=1)
    length              = UnsignedIntField(field_order=5, byte_width=1)
    c_field             = UnsignedIntField(field_order=6, byte_width=1)
    m_field             = UnsignedIntField(field_order=7, byte_width=2, byte_order="big")
    uid                 = UnsignedIntField(field_order=8, byte_width=4, byte_order="big")
    version             = UnsignedIntField(field_order=9, byte_width=1)
    device              = UnsignedIntField(field_order=10, byte_width=1)
    ci_field            = UnsignedIntField(field_order=11, byte_width=1)
    # legacy payload start ---------------------------------------------
    temperature_tmp117  = SignedIntField(field_order=12, byte_width=2)
    mag_x      = SignedIntField(field_order=13, byte_width=2)
    mag_y      = SignedIntField(field_order=14, byte_width=2)
    mag_z      = SignedIntField(field_order=15, byte_width=2)
    acc_x     = SignedIntField(field_order=16, byte_width=2)
    acc_y     = SignedIntField(field_order=17, byte_width=2)
    acc_z     = SignedIntField(field_order=18, byte_width=2)
    acc_tilt_x = SignedIntField(field_order=19, byte_width=2)
    acc_tilt_y = SignedIntField(field_order=20, byte_width=2)
    acc_tilt_z = SignedIntField(field_order=21, byte_width=2)
    pitch_tenth_deg     = SignedIntField(field_order=22, byte_width=2)
    roll_tenth_deg      = SignedIntField(field_order=23, byte_width=2)
    conductivity        = UnsignedIntField(field_order=24, byte_width=2)
    pressure            = UnsignedIntField(field_order=25, byte_width=2)
    temperature_keller  = UnsignedIntField(field_order=26, byte_width=2)
    battery_voltage     = UnsignedIntField(field_order=27, byte_width=2)
    sequence_number     = UnsignedIntField(field_order=28, byte_width=1)
    # legacy payload end -----------------------------------------------
    rssi                = UnsignedIntField(field_order=29, byte_width=1)            

# Define acceptable list of blocks
blocks : dict[bytes,type[Block]] = {
    block.identifier : block for block in [
        Block_A_LSM303,
        Block_B_BMA400,
        Block_C_CHIL,
        Block_D_Datalogger,
        Block_E_Environmental,
        Block_H_Housekeeping,
        Block_K_Keller,
        Block_M_MBusPacket,
        Block_R_Receiver,
        Block_T_Tilt,
        Block_V_Voltage,
        # Legacy
        # Block_W_Wurst
    ]
}