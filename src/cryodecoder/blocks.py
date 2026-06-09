import cryodecoder
import cryodecoder.exceptions

import copy
from abc import ABC, abstractmethod
from enum import Enum
import struct
from typing import Generic, TypeVar, Union, Literal
ValueType = TypeVar('ValueType')
from types import NoneType

##############################################################################
# Fields
##############################################################################
class Field(ABC, Generic[ValueType]):
    """Field defines a generic class which takes raw values in bytes and 
    provides an interface to convert the byte stream into an interpreted value
    """

    def __init__(self, field_order, byte_width = 0, value_default = None):
        self.field_order = field_order
        self.byte_width = byte_width
        self._raw : bytes = b'\x00' * byte_width
        self._value : Union[ValueType, NoneType] = value_default
        self._parent = None

    def __set_name__(self, owner, name):
        self.field_name = name

    @abstractmethod
    def from_bytes(self, raw):
        ...
    @abstractmethod
    def to_bytes(self, value):
        ...

    def __repr__(self):
        return f"{self.field_name}({type(self).__name__}:{self.byte_width} bytes) = {self.value}"

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

class Payload(Field):

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
        raise cryodecoder.exceptions.PayloadAccessError

    # Override the original value method to disable access
    @Field.value.setter
    def value(self, value : bytes):
        raise cryodecoder.exceptions.PayloadAccessError

class UnsignedIntField(Field[int]):

    def __init__(self, field_order, byte_width, byte_order = "little"):
        super().__init__(field_order, byte_width=byte_width, value_default=0)
        self.byte_order = byte_order

    def to_bytes(self, value):
        return int.to_bytes(value, self.byte_width, byteorder=self.byte_order)
    def from_bytes(self, value):
        return int.from_bytes(value, byteorder=self.byte_order)
    
class SignedIntField(Field[int]):

    def __init__(self, field_order, byte_width, byte_order = "little"):
        super().__init__(field_order, byte_width=byte_width, value_default=0)
        self.byte_order = byte_order

    def to_bytes(self, value):
        return int.to_bytes(value, self.byte_width, byteorder=self.byte_order, signed=True)
    def from_bytes(self, value):
        return int.from_bytes(value, byteorder=self.byte_order, signed=True)
    
class IEEE754Float(Field[float]):

    def __init__(self, field_order):
        super().__init__(field_order, byte_width=4, value_default=0)

    def to_bytes(self, value):
        return struct.pack("<f", value)
    def from_bytes(self, value):
        return struct.unpack("<f", value)
    
#-----------------------------------------------------------------------------
# Specific field types
#-----------------------------------------------------------------------------
class TemperatureTMP117Field(SignedIntField):

    @property
    def convertedValue(self):
        return self._value / 128
    
    @convertedValue.setter
    def convertedValue(self, temperatureValue : float):
        self._value = int(temperatureValue * 128)
        self._raw = self.to_bytes(self._value)

class TemperatureSHT30Field(UnsignedIntField):

    @property
    def convertedValue(self):
        return -45 + 175 * (self._value)/(2**16-1)
    
    @convertedValue.setter
    def convertedValue(self, temperatureValue : float):
        rawValue = (temperatureValue + 45) * (2**16 - 1) / 175
        self._value = rawValue
        self._raw = self.to_bytes(self._value)

class RelativeHumiditySHT30Field(UnsignedIntField):

    @property
    def convertedValue(self):
        return 100 * (self._value)/(2**16-1)
    
    @convertedValue.setter
    def convertedValue(self, temperatureValue : float):
        rawValue = temperatureValue * (2**16 - 1) / 100
        self._value = rawValue
        self._raw = self.to_bytes(self._value)

class TemperatureKellerField(UnsignedIntField):

    @property
    def convertedValue(self):
        return 100 * (self._value)/(2**16-1)
    
    @convertedValue.setter
    def convertedValue(self, temperatureValue : float):
        rawValue = temperatureValue * (2**16 - 1) / 100
        self._value = rawValue
        self._raw = self.to_bytes(self._value)


##############################################################################
# Blocks
##############################################################################
class BlockHeader: # L1(BlockHeader):
    length_byte_width : int = 1
    def to_bytes(self, block) -> bytes:
        # Calculate length
        length = self.calculate_block_length(block)
        # Return header
        return block.identifier + \
            int.to_bytes(length, self.length_byte_width, byteorder="little")
    def length(self) -> int:
        return self.length_byte_width + 1
    def calculate_block_length(self, block):
        # Start wiht the field bytes
        block_length = block.count_field_bytes()
        # Check whether we have a L2/L3 block
        if isinstance(block, BlockChildren):
            # then iterate through children
            for child in block.children:
                if isinstance(child, BlockChildren):
                    # Only valid for two levels of iteration
                    for grandchild in child.children:
                        block_length += len(grandchild)
                block_length += len(child)
        # return the final count
        return block_length
    
class BlockHeaderL3(BlockHeader):
    length_byte_width : int = 2


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

class Block:

    # Use an abstract class as the default header to ensure override
    header_class = BlockHeader

    # Block level corresponds to Data, Origin or Context (L1, L2 or L3) blocks
    level : BlockLevel = BlockLevel.L1 # defaulting to L1

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
    
    def getChild(self, block_type : type) -> Union[Block, NoneType]:
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
    identifier = b'A'
    header_class = BlockHeader
    mag_x = SignedIntField(field_order=0, byte_width=2)
    mag_y = SignedIntField(field_order=1, byte_width=2)
    mag_z = SignedIntField(field_order=2, byte_width=2)
    acc_x = SignedIntField(field_order=3, byte_width=2)
    acc_y = SignedIntField(field_order=4, byte_width=2)
    acc_z = SignedIntField(field_order=5, byte_width=2)

class Block_B_BMA400(Block):
    identifier = b'B'
    header_class = BlockHeader
    acc_x = SignedIntField(field_order=0, byte_width=2)
    acc_y = SignedIntField(field_order=1, byte_width=2)
    acc_z = SignedIntField(field_order=2, byte_width=2)
    
class Block_C_CHIL(Block):
    identifier         = b'C'
    header_class       = BlockHeader
    sequence_number    = UnsignedIntField(field_order=0, byte_width=1)
    voltage_battery    = UnsignedIntField(field_order=1, byte_width=2)
    conductivity       = UnsignedIntField(field_order=2, byte_width=2)
    temperature_tmp117 = TemperatureTMP117Field(field_order=3, byte_width=2)

class Block_E_Environmental(Block):
    identifier = b'E'
    header_class = BlockHeader
    pressure_ms5607    = IEEE754Float(field_order=0)
    temperature_ms5607 = IEEE754Float(field_order=1)
    temperature_sht30  = TemperatureSHT30Field(field_order=2, byte_width=2)
    humidity_sht30     = RelativeHumiditySHT30Field(field_order=3, byte_width=2)

class Block_K_Keller(Block):
    identifier = b'K'
    header_class = BlockHeader
    pressure = UnsignedIntField(field_order=0, byte_width=2)
    temperature = UnsignedIntField(field_order=1, byte_width=2)
    date_code = UnsignedIntField(field_order=2, byte_width=1)
    pressure_min = IEEE754Float(field_order=3)
    pressure_max = IEEE754Float(field_order=4)

class Block_V_Voltage(Block):
    identifier = b'V'
    header_class = BlockHeader
    voltage_battery   = UnsignedIntField(field_order=0, byte_width=2)
    voltage_shunt_ch1 = UnsignedIntField(field_order=1, byte_width=2)
    voltage_bus_ch1   = UnsignedIntField(field_order=2, byte_width=2)
    voltage_shunt_ch2 = UnsignedIntField(field_order=3, byte_width=2)
    voltage_bus_ch2   = UnsignedIntField(field_order=4, byte_width=2)
    voltage_shunt_ch3 = UnsignedIntField(field_order=5, byte_width=2)
    voltage_bus_ch3   = UnsignedIntField(field_order=6, byte_width=2)

class Block_T_Tilt(Block):
    identifier = b'T'
    header_class = BlockHeader
    acc_x = UnsignedIntField(field_order=0, byte_width=2)
    acc_y = UnsignedIntField(field_order=1, byte_width=2)
    acc_z = UnsignedIntField(field_order=2, byte_width=2)
    pitch_tenth_deg = UnsignedIntField(field_order=3, byte_width=2)
    roll_tenth_deg  = UnsignedIntField(field_order=4, byte_width=2)

class Block_M_MBusPacket(BlockChildren):
    identifier     = b'M'
    level          = BlockLevel.L2
    header_class   = BlockHeader
    channel_number = UnsignedIntField(field_order=0, byte_width=1)
    c_field  = UnsignedIntField(field_order=1, byte_width=1)
    m_field  = UnsignedIntField(field_order=2, byte_width=2, byte_order="big")
    uid      = UnsignedIntField(field_order=3, byte_width=4, byte_order="big")
    version  = UnsignedIntField(field_order=4, byte_width=1)
    device   = UnsignedIntField(field_order=5, byte_width=1)
    ci_field = UnsignedIntField(field_order=6, byte_width=1)
    payload  = Payload(field_order=7)
    rssi     = UnsignedIntField(field_order=8, byte_width=1)

class Block_R_Receiver(BlockChildren):
    identifier     = b'R'
    level          = BlockLevel.L2
    header_class   = BlockHeader
    payload  = Payload(field_order=0)
    
class Block_D_Datalogger(BlockChildren):
    identifier = b'D'
    level = BlockLevel.L3
    header_class = BlockHeaderL3
    receiver_id     = UnsignedIntField(field_order=0, byte_width=4)
    timestamp       = UnsignedIntField(field_order=1, byte_width=4)
    sequence_number = UnsignedIntField(field_order=2, byte_width=1)
    payload         = Payload(field_order=3)

# Define acceptable list of blocks
blocks : dict[bytes,type[Block]] = {
    block.identifier : block for block in [
        Block_A_LSM303,
        Block_B_BMA400,
        Block_C_CHIL,
        Block_D_Datalogger,
        Block_E_Environmental,
        Block_K_Keller,
        Block_M_MBusPacket,
        Block_R_Receiver,
        Block_T_Tilt,
        Block_V_Voltage
    ]
}