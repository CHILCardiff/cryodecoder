import cryodecoder

import copy
from abc import ABC, abstractmethod
import struct
from typing import Generic, TypeVar, Union
ValueType = TypeVar('ValueType')
from types import NoneType

class Field(ABC, Generic[ValueType]):

    def __init__(self, field_order, byte_width = 0, value_default = None):
        self.field_order = field_order
        self.byte_width = byte_width
        self._raw : bytes = b'\x00' * byte_width
        self._value : Union[ValueType, NoneType] = value_default

    def __set_name__(self, owner, name):
        self.field_name = name

    @abstractmethod
    def from_bytes(self, raw):
        ...
    @abstractmethod
    def to_bytes(self, value):
        ...

    @property
    def raw(self):
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
        return self._value
    @value.setter
    def value(self, value : ValueType):
        self._value = value
        self._raw = self.to_bytes(value) or b''

class UnsignedIntField(Field[int]):

    def __init__(self, field_order, byte_width):
        super().__init__(field_order, byte_width=byte_width, value_default=0)

    def to_bytes(self, value):
        return int.to_bytes(value, self.byte_width, "little")
    def from_bytes(self, value):
        return int.from_bytes(value, "little")
    
class SignedIntField(Field[int]):

    def __init__(self, field_order, byte_width):
        super().__init__(field_order, byte_width=byte_width, value_default=0)

    def to_bytes(self, value):
        return int.to_bytes(value, self.byte_width, "little", signed=True)
    def from_bytes(self, value):
        return int.from_bytes(value, "little", signed=True)
    
class IEEE754Float(Field[int]):

    def __init__(self, field_order):
        super().__init__(field_order, byte_width=4, value_default=0)

    def to_bytes(self, value):
        return struct.pack("<f4", value)
    def from_bytes(self, value):
        return struct.unpack("<f4", value)

class BlockHeader(ABC):
    @abstractmethod
    def to_bytes(self):
        ...

class BlockHeaderL1(BlockHeader):
    length_byte_width = 1
    def to_bytes(self, block) -> bytes:
        # Calculate length
        length = block.count_field_bytes()
        # Return header
        return block.identifier + \
            int.to_bytes(length, self.length_byte_width, byteorder="little")

class Block:

    # Use an abstract class as the default header to ensure override
    header_class = BlockHeader

    def __init__(self, **kwargs):
        """
        When we initialise a block, check for the all the attributes
        which derive from Field and convert these into instance variables
        """
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

    def to_bytes(self):
        field_bytes = b''
        for field in self.fields:
            field_bytes += field.raw
        return self.header.to_bytes(self) + field_bytes
        
    def count_field_bytes(self):
        length = 0
        for field in self.fields:
            length += field.byte_width
        return length

###############################################################################
# BLOCK DEFINITIONS
###############################################################################
class Block_A_LSM303(Block):
    identifer = b'A'
    header_class = BlockHeaderL1
    mag_x = SignedIntField(field_order=0, byte_width=2)
    mag_y = SignedIntField(field_order=1, byte_width=2)
    mag_z = SignedIntField(field_order=2, byte_width=2)
    acc_x = SignedIntField(field_order=3, byte_width=2)
    acc_y = SignedIntField(field_order=4, byte_width=2)
    acc_z = SignedIntField(field_order=5, byte_width=2)

class Block_B_BMA400(Block):
    identifier = b'B'
    header_class = BlockHeaderL1
    acc_x = SignedIntField(field_order=0, byte_width=2)
    acc_y = SignedIntField(field_order=1, byte_width=2)
    acc_z = SignedIntField(field_order=2, byte_width=2)
    
class Block_C_CHIL(Block):
    identifier         = b'C'
    header_class       = BlockHeaderL1
    sequence_number    = UnsignedIntField(field_order=0, byte_width=1)
    voltage_battery    = UnsignedIntField(field_order=1, byte_width=2)
    conductivity       = UnsignedIntField(field_order=2, byte_width=2)
    temperature_tmp117 = UnsignedIntField(field_order=3, byte_width=2)

class Block_E_Environmental(Block):
    identifier = b'E'
    header_class = BlockHeaderL1
    pressure_ms5607    = IEEE754Float(field_order=0)
    temperature_ms5607 = IEEE754Float(field_order=1)
    temperature_sht30  = UnsignedIntField(field_order=2, byte_width=2)
    humidity_sht30     = UnsignedIntField(field_order=3, byte_width=2)

class Block_K_Keller(Block):
    identifier = b'K'
    header_class = BlockHeaderL1
    pressure = UnsignedIntField(field_order=0, byte_width=2)
    temperature = UnsignedIntField(field_order=1, byte_width=2)
    date_code = UnsignedIntField(field_order=2, byte_width=1)
    pressure_min = IEEE754Float(field_order=3)
    pressure_max = IEEE754Float(field_order=4)

class Block_V_Voltage(Block):
    identifier = b'V'
    header_class = BlockHeaderL1
    voltage_battery   = UnsignedIntField(field_order=0, byte_width=2)
    voltage_shunt_ch1 = UnsignedIntField(field_order=1, byte_width=2)
    voltage_bus_ch1   = UnsignedIntField(field_order=2, byte_width=2)
    voltage_shunt_ch2 = UnsignedIntField(field_order=3, byte_width=2)
    voltage_bus_ch2   = UnsignedIntField(field_order=4, byte_width=2)
    voltage_shunt_ch3 = UnsignedIntField(field_order=5, byte_width=2)
    voltage_bus_ch3   = UnsignedIntField(field_order=6, byte_width=2)