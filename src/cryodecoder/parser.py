from abc import ABC, abstractmethod
import argparse 
import datetime
import logging
import pathlib
import serial

from os import PathLike
from typing import Union, Literal, Optional

import cryodecoder
import cryodecoder.blocks
import cryodecoder.exceptions

# Define a decorator for the parser stack
def _parserstackfunction(method):
    def stackmethod(self, index=None):
        if index is None:
            return method(self, self._stack)
        else:
            return method(self, index)
    return stackmethod

class Parser:
    """
    The :py:class:`Parser` object implements the logic to decode CHIL instrument packets and previous versions
    

    ."""

    def __init__(self, async_input : bool = False):
        """
        :param async_input: set to *True* if bytes are expected to be delivered asynchronously (i.e. over a USB decoder). Defaults to *False*.
        :type async_input: bool
        """
        # Is the parser expecting asynchronous input
        self._async = async_input
        # Buffer to store valid blocks in
        self._blocks = []
        # Buffer to store input to
        self._buffer : bytes = b''
        self._timestamp_buffer : list[datetime.datetime] = []
        self._last_timestamp = None
        # Stack values
        self.reset_stack_variables()
        # Setup state
        self._state = Parser.state_readIdentifier
            
    def reset_stack_variables(self):
        """
        resets the internal state variables that implement the parser logic.
        """
        # Stack values
        self._stack = 0
        self._length_bytes     = 0
        self._init_level       = None
        self._block_length : list[int] = [None,None,None]
        self._bytes_remaining : list[int]  = [None, None, None]
        self._fields_remaining : list[int] = [None, None, None]
        self._block : list[cryodecoder.blocks.Block] = [None,None,None]
        return
    
    def push(self, raw : bytes):
        """assign raw data to local raw buffer
        """
        self._buffer += raw
        self._timestamp_buffer.append(datetime.datetime.now(datetime.UTC))
        self._last_timestamp = self._timestamp_buffer[-1]

    def pop(self, count=1):
        """pop the top off the buffer
        """
        if len(self._buffer) >= count + 1:
            self._buffer = self._buffer[count:]
            self._timestamp_buffer = self._timestamp_buffer[count:]
        else:
            self._buffer = b''
            self._timestamp_buffer = []

    def complete(self):
        """if we have finished processing the buffer, return true

        TODO: add more relevant termination conditions here, including an
        'infinite' processing mode when using a Serial/asyncronous decoder
        """

        # Define series of conditions for whether the parsing is complete
        # ------------------------------------------------------------------
        # If we are in asynchronous input mode, we keep parsing ad-infinitem
        if self._async:
            return False
        else:
            if len(self._buffer) == 0 and \
                self._state != Parser.state_appendBlock:
                # Reset the stack
                self.reset_stack_variables()
                # and return complete
                return True
            else:
                # otherwise we still have bytes to process
                return False
        
    def available(self):
        return len(self._blocks)

    def read(self) -> Union[NoneType, tuple[datetime.datetime, cryodecoder.blocks.Block]]:
        """return the next available block
        """
        if self.available():
            # Return first block
            return self._blocks.pop(0)
        
        else:
            return None
        
    def update(self):
        self._state(self)

    def state_readIdentifier(self):

        # print(f"DBG - [rI | fields({self._fields_remaining}), bytes({self._bytes_remaining})]")

        # Invalid block
        if not self._buffer[0:1] in cryodecoder.blocks.blocks:
            # print(f"DBG - [rI] Invalid identifier {self._buffer[0:1]}, {self._fields_remaining[self._stack]}, {self._bytes_remaining[self._stack]}")
            
            # We might have come from the end of a block with an extra field
            if self._fields_remaining[self._stack] is not None and \
               self._bytes_remaining[self._stack] is not None and \
               self._fields_remaining[self._stack] > 0 and \
               self._bytes_remaining[self._stack] > 0:
                self._state = Parser.state_readField
                return
            # Otherwise, it's simply and invalid identifier
            else:
                self.pop()
                return
            
        # We might have come from the end of a block with an extra field

        if self._fields_remaining[self._stack] is not None and \
            self._bytes_remaining[self._stack] is not None and \
            self._fields_remaining[self._stack] > 0 and \
            self._bytes_remaining[self._stack] > 0:
            # Remaining bytes in this block's fields 
            bytes_remaining_in_fields = sum(
                [field.byte_width for field in self._block[self._stack].fields[-self._fields_remaining[self._stack]:]]
            )
            if self._bytes_remaining[self._stack] == bytes_remaining_in_fields:
                self._state = Parser.state_readField
                return
        
        # Get block type
        block_type = cryodecoder.blocks.blocks[self._buffer[0:1]]
        # print(f"DBG - [rI] Valid identifier {self._buffer[0:1]}")
        
        # If we haven't initialised then 
        if self._init_level is None:
            self._init_level = block_type.level.value
            # Assign block stack based on level
            self._stack = block_type.level.value - 1

        # Check whether the block is less than or equal to the current level
        if block_type.level.value - 1 <= self._stack:
            self._stack = block_type.level.value - 1
        else:
            # print(f"DBG - Invalid level {block_type.level.value} (stack={self._stack + 1})")
            self.pop()
            return
        
        # print(f"DBG - Setting stack to {self._stack}")

        # Assign block type
        self._block[self._stack] = block_type()

        # get rid of top of the buffer, we've stored the block type
        self.pop()
        # and decrease the byte count for every block above this
        for level in range(self._stack + 1, self._init_level):
            self._bytes_remaining[level] -= 1

        # Move to next state
        self._state = Parser.state_readLength
        # Assign fields remaining
        self._fields_remaining[self._stack] = len(self._block[self._stack].fields)

        return

    def state_readLength(self):

        # print(f"DBG - [rL | fields({self._fields_remaining}), bytes({self._bytes_remaining})]")

        length_bytes = self._block[self._stack].header.length_byte_width
        # Check if we don't have enough bytes to read in a full block
        if len(self._buffer) < length_bytes:
            # keep waiting
            return 
        
        # Get length
        length = self._buffer[0:length_bytes]

        # We need to check here that we're not dealing with a legacy 'C' block
        # that would have a length identifier of '0' or '1'.
        if self._block[self._stack].identifier == b'C':
            if length in (b'0', b'1'):
                print(f"Mutating 'C' block to legacy format.")
                self._block[self._stack] = cryodecoder.blocks.Block_C_Cryoegg()
                self._fields_remaining[self._stack] = len(self._block[self._stack].fields)

        if isinstance(self._block[self._stack].header, cryodecoder.blocks.BlockHeaderLegacy):
            # Get the legacy field length
            legacy_byte_length = self._block[self._stack].header.get_bytes_remaining(self._block[self._stack].identifier, classifier=length)
            # Then allocate the correct size
            self._bytes_remaining[self._stack] = legacy_byte_length
            self._block_length[self._stack] = legacy_byte_length
        else:
            # print(f"DBG - Reading {length_bytes} bytes as length={length}")
            # Assign bytes remaining
            self._bytes_remaining[self._stack] = int.from_bytes(length, "little")
            self._block_length[self._stack] = int.from_bytes(length, "little")

        # If we have bytes or fields remaining then read a field, otherwise
        # we go straight to appending a block
        if self._bytes_remaining[self._stack] or self._fields_remaining[self._stack]:
            # Drop the length, we've stored this
            self.pop(length_bytes)
            # and decrease the byte count for every block above this
            for level in range(self._stack + 1, self._init_level):
                self._bytes_remaining[level] -= length_bytes
            # move to readField
            self._state = Parser.state_readField
            return
        else:
            # otherwise, try and append this block
            self._state = Parser.state_appendBlock
            self.update()
            return

        return

    def state_readField(self):

        # print(f"DBG - [rF | fields({self._fields_remaining}), bytes({self._bytes_remaining})]")
        
        # Calculate index of the field we're dealing with
        field_index = len(self._block[self._stack].fields) - self._fields_remaining[self._stack]
        # Store field
        field = getattr(self._block[self._stack], self._block[self._stack].fields[field_index].field_name)

        # Check if we have a payload byte
        if isinstance(field, cryodecoder.blocks.Payload):
            # Decrease field count
            self._fields_remaining[self._stack] -= 1
            # Go to readIdentifier
            self._state = Parser.state_readIdentifier
            return

        # Otherwise, we need to read the field in
        if len(self._buffer) < field.byte_width:
            # stay in this state
            return
        else:
            # print(f"DBG - Assinging {field.field_name} as {self._buffer[0:field.byte_width]}")
            # We have enough bytes
            field.raw = self._buffer[0:field.byte_width]
            # Decrease the field count
            self._fields_remaining[self._stack] -= 1
            # Decrease bytes for every block including this
            for level in range(self._stack, self._init_level):
                self._bytes_remaining[level] -= field.byte_width
            self.pop(field.byte_width)

        # Now we have determined the field, we need to check whether we are
        # in an MBus block with a CI_FIELD = 0xAA as this will indicate that
        # the packet format is the original one rather than 
        if isinstance(self._block[self._stack], cryodecoder.blocks.Block_M_MBusPacket) and field.field_name == "ci_field" and field.raw == b'\xAA': # Legacy packet
            pass # debug legacy field
            for legacy_class in (
                cryodecoder.blocks.Block_M_MBusPacketCryoegg2023,
                cryodecoder.blocks.Block_M_MBusPacketCryowurst2023,
            ):
                # Create test object
                test_block = legacy_class()
                # Get expected block length of that object
                if self._block_length[self._stack] == \
                    test_block.header.calculate_block_length(test_block):
                    # Increment remaining fields by the difference between
                    # this and the old block
                    self._fields_remaining[self._stack] += \
                    len(test_block.fields) - len(self._block[self._stack].fields)
                    # Convert to new block
                    for field in self._block[self._stack].fields:
                        # Assign existing fields
                        if hasattr(test_block, field.field_name):
                            getattr(test_block, field.field_name).raw = field.raw
                    # Don't need to complete this step for another packet type
                    self._block[self._stack] = test_block
                    break

        # Check whether we have any bytes left
        if self._fields_remaining[self._stack] <= 0:
            if self._bytes_remaining[self._stack] <= 0:
                # Move to append this block
                self._state = Parser.state_appendBlock
                self.update()
                return
            else:
                self._state = Parser.state_readIdentifier 
                return
        else:
            # We still have fields to read
            self._state = Parser.state_readField
            return
            
    def state_appendBlock(self):

        # print(f"DBG - [aB | fields({self._fields_remaining}), bytes({self._bytes_remaining})]")
            
        # Save the block
        block = self._block[self._stack]
        # Make the current block empty
        self._block[self._stack] = None

        # Check we are not at the top of the stack
        if self._stack < self._init_level - 1:

            # Increment the stack
            self._stack += 1
            # implicit guarantee that L2 and L3 blocks are of type BlockChildren - TODO: worth checking?
            self._block[self._stack].add_child(block)
            # print(f"DBG - Assigned {block} to {self._block[self._stack]}")

            # fields == 0 -> no more fields, bytes == 0 -> no more blocks
            if self._fields_remaining[self._stack] == 0 and \
                self._bytes_remaining[self._stack] == 0:
                # then we can append the next block too)
                self._state = Parser.state_appendBlock
                self.update()
                return
            elif self._fields_remaining[self._stack] >= 0 and \
                self._bytes_remaining[self._stack] > 0:
                # We're done processing this block but are expecting
                # another one at the same level
                self._state = Parser.state_readIdentifier
                return
            # elif self._fields_remaining[self._stack] > 0 and :
            #     self._state = Parser.state_readField

        # We are at the top level
        else:

            # Append block to top level
            self._blocks.append((self._last_timestamp, block))
            # print(f"DBG - Assigned {block} to parser stack")
            # print(f"DBG - [{len(self._buffer)}] {self._buffer}")

            # Reset variables
            self.reset_stack_variables()
            self._state = Parser.state_readIdentifier
            return

        return
    
class DataColumn(ABC):

    def __init__(self, column_name):
        self.name = column_name

    def getColumnName(self):
        return self.name

    @abstractmethod
    def getColumnValue(self, block):
        pass

class ReceiverTimestampColumn(DataColumn):

    def getColumnValue(self, block):
        if isinstance(block, (
            cryodecoder.blocks.Block_D_Datalogger, 
            cryodecoder.blocks.Block_H_Housekeeping,
            cryodecoder.blocks.Block_C_Cryoegg,
            cryodecoder.blocks.Block_W_Wurst
        )):
            time = datetime.datetime.fromtimestamp(block.timestamp.value, tz=datetime.UTC)
            return f"{time.strftime("%Y-%m-%d %H:%M:%S")}"
        else:
            return ""
        
class ReceiverIDColumn(DataColumn):

    def getColumnValue(self, block):
        if isinstance(block, cryodecoder.blocks.Block_D_Datalogger) or \
           isinstance(block, cryodecoder.blocks.Block_H_Housekeeping):
            return f"{block.receiver_id.value:x}"
        else:
            return ""
        
class MBusDataColumn(DataColumn):

    def getColumnValue(self, block):

        if isinstance(block, (
            cryodecoder.blocks.Block_C_Cryoegg,
            cryodecoder.blocks.Block_W_Wurst
        )):
            return self.getReceiver2023Value(block)

        mbus_block = None
        if isinstance(block, cryodecoder.blocks.Block_D_Datalogger) or \
           isinstance(block, cryodecoder.blocks.Block_H_Housekeeping):
            mbus_block = block.getChild((
                cryodecoder.blocks.Block_M_MBusPacket,
                cryodecoder.blocks.Block_M_MBusPacketCryoegg2023,
                cryodecoder.blocks.Block_M_MBusPacketCryowurst2023,
            )) # returns None if not a child
        elif isinstance(block, (
            cryodecoder.blocks.Block_M_MBusPacket,
            cryodecoder.blocks.Block_M_MBusPacketCryoegg2023,
            cryodecoder.blocks.Block_M_MBusPacketCryowurst2023,
        )):
            mbus_block = block

        if mbus_block is None:
            return ""
        else:
            return self.getMBusValue(mbus_block)

    @abstractmethod
    def getMBusValue(self, mbus_block):
        ...

    @abstractmethod
    def getReceiver2023Value(self, block):
        ...
        
class ReceiverSequenceNumberColumn(DataColumn):

    def getColumnValue(self, block):
        if isinstance(block, cryodecoder.blocks.Block_D_Datalogger) or \
           isinstance(block, cryodecoder.blocks.Block_H_Housekeeping):
            return f"{block.receiver_id.value:x}"
        else:
            return ""

class ChannelColumn(MBusDataColumn):

    def getMBusValue(self, mbus_block):
        return f"{mbus_block.channel_number.value:01d}"

    def getReceiver2023Value(self, block):
        return f"{block.channel_number.value:01d}"

class UIDColumn(MBusDataColumn):

    def getMBusValue(self, mbus_block):
        return f"{mbus_block.uid.value:08x}"

    def getReceiver2023Value(self, block):
        return f"{block.uid.value:08x}"

class RSSIColumn(MBusDataColumn):

    def getMBusValue(self, mbus_block):
        return f"{-mbus_block.rssi.value / 2}"

    def getReceiver2023Value(self, block):
        return f"{-block.rssi.value / 2}"
    
class L1MBusDataColumn(DataColumn):
    L1_class = None

    @abstractmethod
    def getDataValue(self, block):
        ...
    
    def getDataValuePre2026(self, block):
        return ""

    def getDataValueReceiver2023(self, block):
        return ""

    def getColumnValue(self, block):

        if isinstance(block, (
            cryodecoder.blocks.Block_C_Cryoegg,
            cryodecoder.blocks.Block_W_Wurst,
        )):
            return self.getDataValueReceiver2023(block)

        mbus_block = None
        if isinstance(block, cryodecoder.blocks.Block_D_Datalogger) or \
        isinstance(block, cryodecoder.blocks.Block_H_Housekeeping):
            mbus_block = block.getChild((
                cryodecoder.blocks.Block_M_MBusPacket,
                cryodecoder.blocks.Block_M_MBusPacketCryoegg2023,
                cryodecoder.blocks.Block_M_MBusPacketCryowurst2023))
            
        if isinstance(block, (
            cryodecoder.blocks.Block_M_MBusPacket,
            cryodecoder.blocks.Block_M_MBusPacketCryoegg2023,
            cryodecoder.blocks.Block_M_MBusPacketCryowurst2023
        )
            ):
            mbus_block = block

        # No MBus data in the top level
        if mbus_block is None:
            return ""
        
        if isinstance(mbus_block, (
            cryodecoder.blocks.Block_M_MBusPacketCryoegg2023,
            cryodecoder.blocks.Block_M_MBusPacketCryowurst2023
        )):
            return self.getDataValuePre2026(mbus_block)
        
        data_block = mbus_block.getChild(self.L1_class) 
        if data_block is None:
            return ""
        else:
            return self.getDataValue(data_block)
        
   
class L1ReceiverDataColumn(DataColumn):
    L1_class = None
    
    @abstractmethod
    def getDataValue(self, block):
        ...

    def getDataValueReceiver2023(self, block):
        return ""

    def getColumnValue(self, block):

        if isinstance(block, (
            cryodecoder.blocks.Block_C_Cryoegg,
            cryodecoder.blocks.Block_W_Wurst,
        )):
            return self.getDataValueReceiver2023(block)
        
        rcvr_block = None
        if isinstance(block, cryodecoder.blocks.Block_D_Datalogger) or \
        isinstance(block, cryodecoder.blocks.Block_H_Housekeeping):
            rcvr_block = block.getChild((
                cryodecoder.blocks.Block_R_Receiver))

        # No MBus data in the top leve
        if rcvr_block is None:
            return ""
        
        data_block = rcvr_block.getChild(self.L1_class) 
        if data_block is None:
            return ""
        else:
            return self.getDataValue(data_block)
        
class InstrumentSequenceNumberColumn(L1MBusDataColumn):
    L1_class = cryodecoder.blocks.Block_C_CHIL
    def getDataValuePre2026(self, block):
        return f"{block.sequence_number.value}"
    def getDataValue(self, block):
        return f"{block.sequence_number.value}"
    def getDataValueReceiver2023(self, block):
        return f"{block.sequence_number.value}"
    
class CHILBatteryVoltageColumn(L1MBusDataColumn):
    L1_class = cryodecoder.blocks.Block_C_CHIL
    def getDataValuePre2026(self, block):
        return f"{block.voltage_battery.value}"
    def getDataValue(self, block):
        return f"{block.voltage_battery.value}"
    def getDataValueReceiver2023(self, block):
        return f"{block.battery_voltage.value}"
    
class CHILConductivityColumn(L1MBusDataColumn):
    L1_class = cryodecoder.blocks.Block_C_CHIL
    def getDataValuePre2026(self, block):
        return f"{block.conductivity.value}"
    def getDataValue(self, block):
        return f"{block.conductivity.value}"
    def getDataValueReceiver2023(self, block):
        return f"{block.conductivity.value}"
    
class CHILTemperatureColumn(L1MBusDataColumn):
    L1_class = cryodecoder.blocks.Block_C_CHIL
    def getDataValuePre2026(self, block):
        return f"{block.temperature_pt1000.value}"
    def getDataValue(self, block):
        return f"{block.temperature_tmp117.convertedValue:.7f}"
    def getDataValueReceiver2023(self, block):
        if isinstance(block, cryodecoder.blocks.Block_W_Wurst):
            return f"{block.temperature_tmp117.value}"
        else:
            return ""

class LSM303DataColumn(L1MBusDataColumn):
    L1_class = cryodecoder.blocks.Block_A_LSM303
    def __init__(self, column_name, field_name):
        super().__init__(column_name)
        self.field_name = field_name
    def getDataValue(self, block):
        if hasattr(block, self.field_name):
            return f"{getattr(block, self.field_name).value:d}"
        else:
            return f""
    def getDataValueReceiver2023(self, block):
        if isinstance(block, cryodecoder.blocks.Block_W_Wurst):
            return f"{getattr(block, self.field_name).value:d}"
        else:
            return ""

class CTiTilt05AccDataColumn(L1MBusDataColumn):
    L1_class = cryodecoder.blocks.Block_T_Tilt
    def __init__(self, column_name, field_name):
        super().__init__(column_name)
        self.field_name = field_name
    def getDataValue(self, block):
        if hasattr(block, self.field_name):
            return f"{getattr(block, self.field_name).value:d}"
        else:
            return f""
    def getDataValueReceiver2023(self, block):
        if isinstance(block, cryodecoder.blocks.Block_W_Wurst):
            legacy_field_name = self.field_name[0:4] + "tilt_" + self.field_name[4:]
            return f"{getattr(block, legacy_field_name).value:d}"
        else:
            return ""
        
class CTiTilt05AngleDataColumn(L1MBusDataColumn):
    L1_class = cryodecoder.blocks.Block_T_Tilt
    def __init__(self, column_name, field_name):
        super().__init__(column_name)
        self.field_name = field_name
    def getDataValue(self, block):
        if hasattr(block, self.field_name):
            return f"{getattr(block, self.field_name).value/10:.1f}"
        else:
            return f""
    def getDataValueReceiver2023(self, block):
        if isinstance(block, cryodecoder.blocks.Block_W_Wurst):
            if hasattr(block, self.field_name):
                return f"{getattr(block, self.field_name).value/10:.1f}"
            else:
                return f""
            
        
class KellerPressureColumn(L1MBusDataColumn):
    L1_class = cryodecoder.blocks.Block_K_Keller
    def getDataValue(self, block):
        return f"{block.pressure.convertedValue:.4f}"
    def getDataValueReceiver2023(self, block):
        return f"{block.pressure.value:.4f}"
        
class KellerTemperatureColumn(L1MBusDataColumn):
    L1_class = cryodecoder.blocks.Block_K_Keller
    def getDataValue(self, block):
        return f"{block.temperature.convertedValue:.4f}"
    def getDataValueReceiver2023(self, block):
        return f"{block.temperature_keller.value:.4f}"
        
class KellerDateCodeColumn(L1MBusDataColumn):
    L1_class = cryodecoder.blocks.Block_K_Keller
    def getDataValue(self, block):
        return f"{block.date_code.value:x}"
        
class BMA400DataColumn(L1ReceiverDataColumn):
    L1_class = cryodecoder.blocks.Block_B_BMA400
    def __init__(self, column_name, field_name):
        super().__init__(column_name)
        self.field_name = field_name
    def getDataValue(self, block):
        if hasattr(block, self.field_name):
            return f"{getattr(block, self.field_name).value:d}"
        else:
            return f""
        
class INA3221DataColumn(L1ReceiverDataColumn):
    L1_class = cryodecoder.blocks.Block_V_Voltage
    def __init__(self, column_name, field_name):
        super().__init__(column_name)
        self.field_name = field_name
    def getDataValue(self, block):
        if hasattr(block, self.field_name):
            return f"{getattr(block, self.field_name).value:d}"
        else:
            return f""
    def getDataValueReceiver2023(self, block):
        if self.field_name == "voltage_battery":
            return f"{block.logger_voltage.value}"
        else:
            return ""
        
class SHT30DataColumn(L1ReceiverDataColumn):
    L1_class = cryodecoder.blocks.Block_E_Environmental
    def __init__(self, column_name, field_name):
        super().__init__(column_name)
        self.field_name = field_name
    def getDataValue(self, block):
        if hasattr(block, self.field_name):
            return f"{getattr(block, self.field_name).convertedValue:.4f}"
        else:
            return f""
        
class MS5607DataColumn(L1ReceiverDataColumn):
    L1_class = cryodecoder.blocks.Block_E_Environmental
    def __init__(self, column_name, field_name):
        super().__init__(column_name)
        self.field_name = field_name
    def getDataValue(self, block):
        if hasattr(block, self.field_name):
            return f"{getattr(block, self.field_name).value:.4f}"
        else:
            return f""
    def getDataValueReceiver2023(self, block):
        if self.field_name.startswith("temperature"):
            return f"{block.logger_temperature.value:.4f}"
        elif self.field_name.startswith("pressure"):
            return f"{block.logger_pressure.value:.4f}"
        else:
            return ""
        
class HexColumn(DataColumn):

    def getColumnValue(self, block):
        return block.to_bytes().hex()

class LoggerBase:
    """
    Interface class for defining logger classes
    """
    
    def __init__(self):
        super(LoggerBase, self).__init__()

        # Setup start time of the logger from local timestamp
        self._init_time = datetime.datetime.now(datetime.UTC)

class CSVLogger(LoggerBase):

    def __init__(self, filename : Union[NoneType, PathLike]):

        LoggerBase.__init__(self)
        self.filename = filename

        self.csv_columns = [
            ReceiverTimestampColumn("timestamp_receiver"),
            ReceiverIDColumn("id_received"),
            ChannelColumn("channel"),
            UIDColumn("id_mbus"),
            RSSIColumn("mbus_rssi"),
            InstrumentSequenceNumberColumn("sequence_number_instrument"),
            CHILBatteryVoltageColumn("voltage_battery_mV"),
            CHILConductivityColumn("conductivity_mV"),
            CHILTemperatureColumn("temperature_tmp117_degC"),
            KellerPressureColumn("pressure_keller_bar"),
            KellerTemperatureColumn("temperature_keller_degC"),
            KellerDateCodeColumn("date_code_keller_raw"),
            LSM303DataColumn("mag_lsm303_x", "mag_x"),
            LSM303DataColumn("mag_lsm303_y", "mag_y"),
            LSM303DataColumn("mag_lsm303_z", "mag_z"),
            LSM303DataColumn("acc_lsm303_x", "acc_x"),
            LSM303DataColumn("acc_lsm303_y", "acc_y"),
            LSM303DataColumn("acc_lsm303_z", "acc_z"),
            CTiTilt05AccDataColumn("acc_cti_tilt05_x_mg", "acc_x"),
            CTiTilt05AccDataColumn("acc_cti_tilt05_y_mg", "acc_y"),
            CTiTilt05AccDataColumn("acc_cti_tilt05_z_mg", "acc_z"),
            CTiTilt05AngleDataColumn("pitch", "pitch_tenth_deg"),
            CTiTilt05AngleDataColumn("roll", "roll_tenth_deg"),
            # Receiver information
            ReceiverSequenceNumberColumn("sequence_number_receiver"),
            BMA400DataColumn("acc_receiver_x", "acc_x"),
            BMA400DataColumn("acc_receiver_y", "acc_y"),
            BMA400DataColumn("acc_receiver_z", "acc_z"),
            INA3221DataColumn("voltage_battery_receiver_raw", "voltage_battery"),
            INA3221DataColumn("voltage_shunt_ch1", "voltage_shunt_ch1"),
            INA3221DataColumn("voltage_bus_ch1", "voltage_bus_ch1"),
            INA3221DataColumn("voltage_shunt_ch2", "voltage_shunt_ch2"),
            INA3221DataColumn("voltage_bus_ch2", "voltage_bus_ch2"),
            INA3221DataColumn("voltage_shunt_ch3", "voltage_shunt_ch3"),
            INA3221DataColumn("voltage_bus_ch3", "voltage_bus_ch3"),
            SHT30DataColumn("relative_humidity_sht30", "humidity_sht30"),
            SHT30DataColumn("temperature_sht30_raw", "temperature_sht30"),
            MS5607DataColumn("pressure_ms5607_bar", "pressure_ms5607"),
            MS5607DataColumn("temperature_ms5607_degC", "temperature_ms5607"),
            HexColumn("hex")
        ]

        self.init_csv_logger()

    def init_csv_logger(self, level=logging.INFO):

        # Setup datalogger output logger
        csv_handler   = logging.FileHandler(self.filename)   
        csv_formatter = logging.Formatter('%(message)s')     
        csv_handler.setFormatter(csv_formatter)

        self._csv_logger = logging.Logger("cryodecoder.data", level=level)
        self._csv_logger.setLevel(level)
        self._csv_logger.addHandler(csv_handler)

        # Write header for data
        headers = [column.name for column in self.csv_columns]
        headers.insert(0, "timestamp_pc")
        self._csv_logger.log(logging.INFO, ",".join(headers))

    def logCSV(self, time: datetime.datetime, block: cryodecoder.blocks.Block):
        # Write columns to CSV
        values = [column.getColumnValue(block) for column in self.csv_columns]
        values.insert(0, f"{time.strftime("%Y-%m-%d %H:%M:%S")}")
        self._csv_logger.log(logging.INFO, ",".join(values))

class SerialDecoder(CSVLogger):
    """
    The :py:class:`SerialDecoder` class provides an interface to decode realtime packets transmitted from a CHIL datalogger over a USB serial connection.

    Example usage:

    .. code-block:: Python

        # Create a SerialLogger on COM10 with a 19,200 Hz baud rate and saving
        # in a subfolder of the current directory
        logger = SerialLogger("COM10", file_root = "./my_logger_data")
        logger.run()

    """

    def __init__(self, 
        port : str ="COM1" , 
        baud_rate : int = 19200, 
        file_root : Optional[PathLike] = None, 
        mode : Literal["receiver", "mbus"] = "receiver"
    ):
        """
        :param port: identifier of the COM port
        :type port: str
        :param baud_rate: the baud rate of the serial connection, defaults to 19200
        :type baud_rate: int
        :param file_root: path to where packets should be saved in CSV format.
        :type file_root: Optional[PathLike]
        :param mode: sets whether a CHIL datalogger ("receiver") or Radiocrafts MBus receiver ("mbus") is being used as the USB receiver.
        :type mode: str
        """

        # Initialises creation time
        LoggerBase.__init__(self)

        # Assign file root
        self.file_root = file_root

        # Initialise CSVLogger
        CSVLogger.__init__(
            self, 
            filename=self.getCSVFilename()
        )

        self.port = port
        self.baud_rate = baud_rate

        self._mode = mode
        self._serial = serial.Serial(port, baud_rate)
        self._parser = Parser(async_input=True)

        # Setup logging
        self.__setup_loggers()
       
    def getRoot(self):
        """
        :returns: the parent folder of where file is to be saved
        :rtype: :py:class:`pathlib.Path`
        """

        # Construct time from init
        time = self._init_time.strftime("%Y%m%d_%H%M%S")
    
        if self.file_root is None:
            root = pathlib.Path(".") / "data" / time
        else:
            root = pathlib.Path(self.file_root)        

        # Create directory if it doesn't exist
        if not root.exists():
            root.mkdir(parents=True)

        return root

    def getCSVFilename(self):
        """
        :returns: the name of the CSV file where data is to be saved
        :rtype: :py:class:`pathlib.Path`
        """

        return self.getRoot() / f"data_{self._init_time.strftime("%Y%m%d_%H%M%S")}.csv"

    def getLoggerFilename(self):
        """
        :returns: the name of the log file where the debugging log from the datalogger is to be saved
        :rtype: :py:class:`pathlib.Path`
        """

        return self.getRoot() / f"logger_{self._init_time.strftime("%Y%m%d_%H%M%S")}.log"

    def getRawFilename(self):
        """
        :returns: the name of the .log file where raw binary from the datalogger is to be saved
        :rtype: :py:class:`pathlib.Path`
        """

        return self.getRoot() / f"raw_{self._init_time.strftime("%Y%m%d_%H%M%S")}.log"

    def __setup_loggers(self, level=logging.INFO):

        # Setup datalogger debug logger
        dl_handler   = logging.FileHandler(self.getLoggerFilename())   
        dl_formatter = logging.Formatter('[%(levelname)s] %(asctime)s: %(message)s')     
        dl_handler.setFormatter(dl_formatter)

        dl_logger = logging.getLogger("cryodecoder.logger")
        dl_logger.setLevel(level)
        dl_logger.addHandler(dl_handler)

        # Setup console handler for feedback
        cmd_handler = logging.StreamHandler()
        cmd_formatter = logging.Formatter('[%(levelname)s] %(asctime)s: %(message)s')
        cmd_handler.setFormatter(cmd_formatter)

        cmd_logger = logging.getLogger("cryodecoder.out")
        cmd_logger.setLevel(level)
        cmd_logger.addHandler(cmd_handler)

        # Raw logger
        raw = open(self.getRawFilename(), "w+")

        # Assign logging objects to the decoder
        self.output_logger = dl_logger
        self.output_console = cmd_logger
        self.output_raw = raw

    def __enter__(self):
        pass

    def __exit__(self):
        self.output_raw.close()

    def runReceiver(self):
        """
        :meta private:
        """
        
        while True:
            try:
                byte = self._serial.read(1)
                self.output_raw.write(f"{int.from_bytes(byte):02x}")
                self.output_raw.flush()

                while ((byte != b'') or not self._parser.complete()):
                    # Bit of a hack here to deal with comments
                    if (byte == b'#' and self._parser._state == Parser.state_readIdentifier):
                        # Read until end of line
                        decode_message = ""
                        byte = self._serial.read(1)
                        self.output_raw.write(f"{int.from_bytes(byte):02x}")
                        self.output_raw.flush()

                        while (byte != b'\n' and byte != b'\r'):
                            decode_message += byte.decode("ascii")
                            byte = self._serial.read(1)
                            self.output_raw.write(f"{int.from_bytes(byte):02x}")
                            self.output_raw.flush()

                        byte = self._serial.read(1)
                        
                        self.output_raw.write(f"{int.from_bytes(byte):02x}")
                        self.output_raw.flush()
                        
                        self.output_logger.log(logging.INFO, decode_message)
                    else:
                        # print(f"DBG - {byte.hex()} -> {byte.decode("ascii") if byte[0] < 128 and byte[0] > 32 else f"({byte[0]})"}")
                        self._parser.push(byte)
                        self._parser.update()

                    if self._parser.available():
                        break

                    byte = self._serial.read(1)

                if self._parser.available():
                    self.__processBlocks()

            except UnicodeDecodeError:
                continue

            except KeyboardInterrupt:
                self._serial.close()
                self.save()
                return
            
    def runMBus(self):
        """
        :meta private:
        """

        while True:
            try:
                length = self._serial.read(1)
                packet = self._serial.read(length[0])

                # Synthesize an MBus packet
                mbus_header = b'M' + int.to_bytes(length[0] + 1) + b'\0'
                mbus_packet = mbus_header + packet
                # FORCE RSSI BUG
                mbus_packet = mbus_packet[0:-1]
                mbus_packet += b'B'

                self._parser.push(mbus_packet)
                while (not self._parser.complete()):
                    self._parser.update()

                if self._parser.available():
                    self.__processBlocks()

            except UnicodeDecodeError:
                continue

            except KeyboardInterrupt:
                self._serial.close()
                self.save()
                return


    def run(self):
        """
        begin receiving data over the COM port.
        """

        if self._mode == "receiver": 
            print("Running decoder in receiver mode...")
            self.runReceiver()
        elif self._mode == "mbus":
            print("Running decoder in MBus (RadioCrafts) mode...")
            self.runMBus()
        else:
            print("Invalid receiver mode.")

    def save(self):
        """
        not yet implemented method to save data on exit.
        """
        pass

    def __consoleOutput(self, time, block):

        self.output_console.log(
            logging.INFO,
            f"Received packet"
        )

        mbus_block = None
        rcvr_block = None
        if isinstance(block, (cryodecoder.blocks.Block_D_Datalogger, cryodecoder.blocks.Block_H_Housekeeping)):

            self.output_console.log(
                logging.INFO,
                f"Received datalogger/housekeeping packet ('D' or 'H')"
            )
            
            time = datetime.datetime.fromtimestamp(block.timestamp.value, tz=datetime.UTC)

            self.output_console.log(
                logging.INFO,
                f"Receiver ID #{block.receiver_id.value:x} with onboard time: {time.strftime("%Y-%m-%d %H:%M:%S")}"
            )

            mbus_block = block.getChild((
                cryodecoder.blocks.Block_M_MBusPacket,
                cryodecoder.blocks.Block_M_MBusPacketCryoegg2023,
                cryodecoder.blocks.Block_M_MBusPacketCryowurst2023,
            ))

            rcvr_block = block.getChild((
                cryodecoder.blocks.Block_R_Receiver
            ))

        elif isinstance(block, (
            cryodecoder.blocks.Block_M_MBusPacket,
            cryodecoder.blocks.Block_M_MBusPacketCryoegg2023,
            cryodecoder.blocks.Block_M_MBusPacketCryowurst2023,
        )):
            
            mbus_block = block

            self.output_console.log(
                logging.INFO,
                f"Received MBus packet ('M')"
            )

        elif isinstance(block, (
            cryodecoder.blocks.Block_R_Receiver
        )):
            
            rcvr_block = block

            self.output_console.log(
                logging.INFO,
                f"Received datalogger info packet ('R')"
            )
            
        if mbus_block is not None:

            self.output_console.log(
                logging.INFO,
                f"Instrument ID #{mbus_block.uid.value:x} with RSSI {-mbus_block.rssi.value/2} dBm"
            )

        if rcvr_block is not None:

            rcvr_voltage = rcvr_block.getChild(cryodecoder.blocks.Block_V_Voltage)

            if rcvr_voltage is not None:
                self.output_console.log(
                    logging.INFO,
                    f"Receiver voltage (raw / 65536): {rcvr_voltage.voltage_battery.value}"
                )


    def __processBlocks(self):

        # We've accidentally ended up here
        if not self._parser.available():
            return
        
        while self._parser.available():
            time, block = self._parser.read()
            # Output value to console if available
            self.logCSV(time, block)
            self.__consoleOutput(time, block)


class FileDecoder(CSVLogger):
    """
    The :py:class:`FileDecoder` class provides an interface to decode data stored on the SD cards of CHIL dataloggers and write the processed data to a CSV file.

    Example usage:

    .. code-block:: Python

        # Create a SerialLogger on COM10 with a 19,200 Hz baud rate and saving
        # in a subfolder of the current directory
        logger = FileLogger(

        )
        logger.run()
    """

    def __init__(self, 
        input_file : str | PathLike, 
        output_file : str | PathLike
    ):
        """
        :param input_file: path to the file from a CHIL datalogger to parse, typically ending in a .log extension.
        :type input_file: str | PathLike
        
        :param output_file: path of where to save the parsed data.
        :type input_file: str | PathLike
        """

        self._parser = Parser()
        input_file = pathlib.Path(input_file)
            
        # Check that the input file is valid
        if not input_file.exists():
            raise FileNotFoundError(input_file)

        # If output file is not given then use the input filename and 
        # add .csv to the end
        if len(output_file) == 0:
            output_file = str(pathlib.Path(input_file)) + ".csv"
        else:
            output_file = pathlib.Path(output_file)
            if output_file.is_dir():
                if not output_file.exists():
                    output_file.mkdir(parents=True)
                output_file = output_file / f"{input_file.name}.csv"
            else:
                if not output_file.resolve().parent.exists():
                    output_file.resolve().parent.mkdir(parents=True)

        # Setup input filename
        self.input_file = input_file
        # Initialise CSVLogger
        CSVLogger.__init__(self, output_file)

    def parse(self):
        """
        parse the file and write any blocks encountered to `self.output_file`.
        """
        
        with open(self.input_file, "rb") as fh:

            byte = fh.read(1)
            while (byte != b'' or not self._parser.complete()):
                self._parser.push(byte)
                self._parser.update()
                byte = fh.read(1)
            
        while self._parser.available():
            # Log block to CSV
            parser_out = self._parser.read()
            if parser_out is not None:
                time, block = parser_out
                self.logCSV(time, block)


def parser_main():
    """
    :meta private:
    """

    parser = argparse.ArgumentParser(
            prog='parser.py',
            description='Runs a file-based or Serial decoder for Cryoegg packets.',
            epilog='See [URL] for more help.'
        )
    
    parser.add_argument("type", choices=["serial", "file"]
                        )
    parser.add_argument("-p", "--port", type=str, required=False, default="COM1")
    parser.add_argument("-b", "--baud", type=int, required=False, default=19200)
    parser.add_argument("-m", "--mode", type=str, required=False, default="receiver", choices=["receiver", "mbus"])

    # Input and output files
    parser.add_argument("-i", "--input", type=str, required=False, default="")
    parser.add_argument("-o", "--output", type=str, required=False, default="")

    args = parser.parse_args()

    if args.type == "serial":

        print(f"Starting serial decoder with port {args.port}")

        serialDecoder = SerialDecoder(port=args.port, baud_rate=args.baud, mode=args.mode)
        serialDecoder.run()

    elif args.type == "file":

        # Check we have an input file
        if len(args.input) == 0:
            raise ValueError(
                "--input required when using cryodecoder in 'file' mode.")
        else:

            fileDecoder = FileDecoder(args.input, args.output)
            fileDecoder.parse()
        
    else:

        print("Invalid parser type provided, shutting down.")

if __name__ == "__main__":
    parser_main()