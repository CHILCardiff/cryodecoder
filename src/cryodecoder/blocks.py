import cryodecoder

import copy
from abc import ABC, abstractmethod
import struct
from typing import Generic, TypeVar, Union
ValueType = TypeVar('ValueType')
from types import NoneType

class Field(ABC, Generic[ValueType]):

    def __init__(self, field_order, byte_width = 0):
        self.field_order = field_order
        self.byte_width = byte_width
        self._raw : bytes = b''
        self._value : Union[ValueType, NoneType] = None

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
        super().__init__(field_order, byte_width=byte_width)

    def to_bytes(self, value):
        return int.to_bytes(value, self.byte_width, "little")
    def from_bytes(self, value):
        return int.from_bytes(value, "little")
    
class SignedIntField(Field[int]):

    def __init__(self, field_order, byte_width):
        super().__init__(field_order, byte_width=byte_width)

    def to_bytes(self, value):
        return int.to_bytes(value, self.byte_width, "little", signed=True)
    def from_bytes(self, value):
        return int.from_bytes(value, "little", signed=True)
    
class IEEE754Float(Field[int]):

    def __init__(self, field_order):
        super().__init__(field_order, byte_width=4)

    def to_bytes(self, value):
        return struct.pack("<f4", value)
    def from_bytes(self, value):
        return struct.unpack("<f4", value)

class BlockHeader:
    identifier = b'\x00'
    length_byte_width = 1
    def to_bytes(self):
        # Calculate length
        length = 0
        for attr in dir(self):
            attr_class = getattr(self, attr).__class__
            if issubclass(attr_class, Field):
                length += getattr(self, attr).byte_width
        # Return header
        return self.identifier + \
            int.to_bytes(length, self.length_byte_width, byteorder="little")

class BlockHeaderExtended:
    length_byte_width = 2

class Block(BlockHeader):

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

    def to_bytes(self):
        field_bytes = b''
        for field in self.fields:
            field_bytes += field.raw
        return BlockHeader.to_bytes(self) + field_bytes
        
class Block_C_CHIL(Block, BlockHeader):
    identifier         = b'C'
    sequence_number    = UnsignedIntField(field_order=0, byte_width=1)
    voltage_battery    = UnsignedIntField(field_order=1, byte_width=2)
    conductivity       = UnsignedIntField(field_order=2, byte_width=2)
    temperature_tmp117 = UnsignedIntField(field_order=3, byte_width=2)


