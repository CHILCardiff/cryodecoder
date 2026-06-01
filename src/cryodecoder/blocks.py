import cryodecoder.exceptions

from abc import ABC, abstractmethod
from enum import Enum

from io import BufferedReader

from typing import Union, Type
from types import NoneType
from numpy import signedinteger, unsignedinteger
from .exceptions import InvalidIdentifierError

BLOCK_IDENTIFIER_TYPE = Union[
    bytes, bytearray, int, str
]


def sanitise_identifier(identifier : BLOCK_IDENTIFIER_TYPE) -> bytes:
    # Identifier should be a single byte 
    if isinstance(identifier, int) and identifier >= 0 and identifier < 256:
        return identifier.to_bytes()
    elif isinstance(identifier, (bytes, bytearray)) and len(identifier) == 1:
        return identifier[0:1] 
        # need to index this way to keep it as a bytes object
    elif isinstance(identifier, str):
        if len(bytes(identifier, "utf-8")) == 1:
            return bytes(identifier, "utf-8")
    raise InvalidIdentifierError(identifier)

def is_valid_identifier(identifier : BLOCK_IDENTIFIER_TYPE) -> bool:
    # Check through each block type
    for block_type in cryodecoder.identifier_register:
        # See if we have the identifier in the register 
        if not sanitise_identifier in cryodecoder.identifier_register[block_type]:
            # if not, skip through and check next
            continue
        else:
            # otherwise, return true
            return True
    # By now, we've not found anything so can return False
    return False

def get_block_level_from_class(block_class : Type):
    # Use the block class to determine which level we are on
    if issubclass(block_class, L1DataBlock):
        return 1
    elif issubclass(block_class, L2OriginBlock):
        return 2
    elif issubclass(block_class, L3ContextBlock):
        return 3
    return 0

def get_block_class_from_identifier(identifier : BLOCK_IDENTIFIER_TYPE) -> Type:
    # Check through each block type
    for block_type in cryodecoder.identifier_register:
        # See if we have the identifier in the register 
        s_identifier = sanitise_identifier(identifier)
        if not s_identifier in cryodecoder.identifier_register[block_type]:
            # if not, skip through and check next
            continue
        else:
            # otherwise, return true
            return cryodecoder.identifier_register[block_type][s_identifier]
    # By now, we've not found anything so can return False
    return None

def validate_int8(val):
    if isinstance(val, bytes):
        return int.from_bytes(val, byteorder="little", signed=True)
    if not isinstance(val, (int, signedinteger)):
        raise TypeError(f"Value {val} must be int or numpy signed integer")
    if val < -128 or val > 127:
        raise ValueError(f"Value {val} must be within -128 to 127 (inclusive).")
    return val

def validate_uint8(val):
    if isinstance(val, bytes):
        return int.from_bytes(val, byteorder="little", signed=False)
    if not isinstance(val, (int, unsignedinteger)):
        raise TypeError("Value must be int or numpy unsigned integer")
    if val < 0 or val > 255:
        raise ValueError("Value must be within 0 to 255 (inclusive)")
    return val

def validate_int16(val):
    if isinstance(val, bytes):
        return int.from_bytes(val, byteorder="little", signed=True)
    if not isinstance(val, (int, signedinteger)):
        raise TypeError(f"Value {val} must be int or numpy signed integer")
    if val < -32768 or val > 32767:
        raise ValueError(f"Value {val} must be within -32,768 to 32,767 (inclusive).")
    return val

def validate_uint16(val):
    if isinstance(val, bytes):
        return int.from_bytes(val, byteorder="little", signed=False)
    if not isinstance(val, (int, unsignedinteger)):
        raise TypeError("Value must be int or numpy unsigned integer")
    if val < 0 or val > 65535:
        raise ValueError("Value must be within 0 to 65,535 (inclusive).")
    return val

def validate_ieee754(val):
    raise ValueError()

class Unit:
    def __init__(self, name : str, si_unit : Union[str, NoneType] = None):
        self.name = name
        self.si_unit = si_unit
    def __eq__(self, comparison):
        if isinstance(comparison, self.__class__) or issubclass(comparison, self.__class__):
            return self.name == comparison.name
        else:
            return False
        
class Unitless(Unit):
    def __init__(self):
        super().__init__(name = "unitless", si_unit = None)

class Field(ABC):
    def __init__(self, name : str, width : Union[int, NoneType] = None, value = None, unit : Union[str, Unit] = Unitless()): 
        self.name = name
        self.value = value
        self.byte_width = width
        self.unit = unit
    
    @abstractmethod
    def to_bytes(self):
        ...
    @abstractmethod
    def from_bytes(self):
        ...

class AbstractBlock(ABC):

    identifier = None

    def __init__(self, identifier):
        self.identifier = sanitise_identifier(identifier)
        self.length = 0

        # Assign fields
        for attribute in dir(self):
            if isinstance(getattr(self, attribute), Field):
                setattr(self, attr) = 

    @abstractmethod
    def to_bytes(self):
        """
        return a byte representation of the block
        """
        ...
    
    @staticmethod
    @abstractmethod
    def validate_length(length):
        """
        return True if the length parameter is valid for the Block type, 
        otherwise return False
        """
        ...

class L1DataBlock(AbstractBlock):
    pass

class L2OriginBlock(AbstractBlock):
    pass

class Uint32Field(Field):

    def to_bytes(self):
        if self.value != None:
            return int.to_bytes(self.value, 4, "little")
        else:
            raise ValueError("Trying to convert NoneType value")
        
    def from_bytes(self):
        if self.value != None:
            return int.from_bytes(self.value, "little")
        else:
            raise ValueError("Trying to convert NoneType value")

class L3ContextBlock(AbstractBlock):

    HEADER_NUM_BYTES = 3

    # Default members of L3 block
    receiver_id = Uint32Field("receiver_id", 4),
    timestamp = Uint32Field("timestamp", 4),
    receiver_sequence_number = Uint32Field("receiverse_sequence_number", 1)

    def __init__(self):
        # Initialise class
        super().__init__(self.identifier)
        # Children blocks
        self.children = []

    

# Define L1 block types
class LSM303AGRBlock(L1DataBlock):
    identifier = 'A'

    @property
    def mag_x(self):
        return self._mag_x
    @mag_x.setter
    def mag_x(self, value):
        self._mag_x = validate_int16(value)
    @property
    def mag_y(self):
        return self._mag_y
    @mag_y.setter
    def mag_y(self, value):
        self._mag_y = validate_int16(value)
    @property
    def mag_z(self):
        return self._mag_z
    @mag_z.setter
    def mag_z(self, value):
        self._mag_z = validate_int16(value)
    @property
    def acc_x(self):
        return self._acc_x
    @acc_x.setter
    def acc_x(self, value):
        self._acc_x = validate_int16(value)
    @property
    def acc_y(self):
        return self._acc_y
    @acc_y.setter
    def acc_y(self, value):
        self._acc_y = validate_int16(value)
    @property
    def acc_z(self):
        return self._acc_z
    @acc_z.setter
    def acc_z(self, value):
        self._acc_z = validate_int16(value)

    def __init__(self, mag_x, mag_y, mag_z, acc_x, acc_y, acc_z):
        # Assign identifier
        super().__init__(self.identifier)
        self.mag_x = mag_x
        self.mag_y = mag_y
        self.mag_z = mag_z
        self.acc_x = acc_x
        self.acc_y = acc_y
        self.acc_z = acc_z

    # def to_bytes(self):
        
    #     # Start with empty string
    #     output = b''
    #     # Append identifier
    #     output = self.identifier
    #     length = 12
    #     output += int.to_bytes(length, byteorder="little")
    #     output += self.mag_x.to_bytes(2, byteorder="little", signed=True)
    #     output += self.mag_y.to_bytes(2, byteorder="little", signed=True)
    #     output += self.mag_z.to_bytes(2, byteorder="little", signed=True)
    #     output += self.acc_x.to_bytes(2, byteorder="little", signed=True)
    #     output += self.acc_y.to_bytes(2, byteorder="little", signed=True)
    #     output += self.acc_z.to_bytes(2, byteorder="little", signed=True)

    #     return output

    @staticmethod
    def validate_length(length):
        raise NotImplementedError()

class BMA400Block(L1DataBlock):
    identifier = 'B'

class CryoBlock(L1DataBlock):
    """
    The CryoBlock ('C') describes electrical conductivity, tmeperature, battery voltage and sequence information associated with a CHIL instrument. 
    """
    identifier = 'C'

class EnvironmentalBlock(L1DataBlock):
    identifier = 'E'

class KellerPressureBlock(L1DataBlock):
    identifier = 'K'

class CTiTiltBlock(L1DataBlock):
    identifier = 'T'

class PowerStatusBlock(L1DataBlock):
    identifier = 'V'


# Define L2 block types
class MBusOriginBlock(L2OriginBlock):
    identifier = 'M'

class ReceiverOriginBlock(L2OriginBlock):
    identifier = 'R'

# Define L2 block types
class DataContextBlock(L3ContextBlock):
    identifier = 'D'

class HousekeepingContextBlock(L3ContextBlock):
    identifier = 'H'