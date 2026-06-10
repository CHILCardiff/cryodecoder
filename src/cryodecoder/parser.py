from abc import ABC, abstractmethod
import argparse 
import datetime
import logging
import pathlib
import serial

from os import PathLike
from typing import Union
from types import NoneType

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

    def __init__(self):
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
        """
        return len(self._buffer) == 0 and self._init_level == None # TODO: add some state relevant condition here

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

        # print(f"[rI | fields({self._fields_remaining}), bytes({self._bytes_remaining})]")

        # Invalid block
        if not self._buffer[0:1] in cryodecoder.blocks.blocks:
            # print(f"[rI] Invalid identifier {self._buffer[0:1]}, {self._fields_remaining[self._stack]}, {self._bytes_remaining[self._stack]}")
            
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
        
        # Get block type
        block_type = cryodecoder.blocks.blocks[self._buffer[0:1]]
        # print(f"[rI] Valid identifier {self._buffer[0:1]}")
        
        # If we haven't initialised then 
        if self._init_level is None:
            self._init_level = block_type.level.value
            # Assign block stack based on level
            self._stack = block_type.level.value - 1

        # Check whether the block is less than or equal to the current level
        if block_type.level.value - 1 <= self._stack:
            self._stack = block_type.level.value - 1
        else:
            # print(f"Invalid level {block_type.level.value} (stack={self._stack + 1})")
            self.pop()
            return
        
        # print(f"Setting stack to {self._stack}")

        # Assign block type
        self._block[self._stack] = block_type()

        # get rid of top of the buffer, we've stored the block type
        self.pop()
        # and decrease the byte count for every block above this
        for level in range(self._stack + 1, self._init_level):
            self._bytes_remaining[level] -= 1

        # Move to next state
        self._state = Parser.state_readLength
        return

    def state_readLength(self):

        # print(f"[rL | fields({self._fields_remaining}), bytes({self._bytes_remaining})]")

        length_bytes = self._block[self._stack].header.length_byte_width
        # Check if we don't have enough bytes to read in a full block
        if len(self._buffer) < length_bytes:
            # keep waiting
            return 
        
        # Get length
        length = self._buffer[0:length_bytes]
        
        # print(f"Reading {length_bytes} bytes as length={length}")
        # Assign bytes remaining
        self._bytes_remaining[self._stack] = int.from_bytes(length, "little")
        self._block_length[self._stack] = int.from_bytes(length, "little")
        # Assign fields remaining
        self._fields_remaining[self._stack] = len(self._block[self._stack].fields)

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

        # print(f"[rF | fields({self._fields_remaining}), bytes({self._bytes_remaining})]")
        
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
            # print(f"Assinging {field.field_name} as {self._buffer[0:field.byte_width]}")
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

        # print(f"[aB | fields({self._fields_remaining}), bytes({self._bytes_remaining})]")
            
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
            # print(f"Assigned {block} to {self._block[self._stack]}")

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
            # print(f"Assigned {block} to parser stack")
            # print(f"[{len(self._buffer)}] {self._buffer}")

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
        if isinstance(block, cryodecoder.blocks.Block_D_Datalogger) or \
           isinstance(block, cryodecoder.blocks.Block_H_Housekeeping):
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

class UIDColumn(MBusDataColumn):

    def getMBusValue(self, mbus_block):
        return f"{mbus_block.uid.value:08x}"

class RSSIColumn(MBusDataColumn):

    def getMBusValue(self, mbus_block):
        return f"{-mbus_block.rssi.value / 2}"
    
class L1MBusDataColumn(DataColumn):
    L1_class = None
    
    @abstractmethod
    def getDataValue(self, block):
        ...
    
    def getDataValuePre2026(self, block):
        return ""

    def getColumnValue(self, block):

        mbus_block = None
        if isinstance(block, cryodecoder.blocks.Block_D_Datalogger) or \
        isinstance(block, cryodecoder.blocks.Block_H_Housekeeping):
            mbus_block = block.getChild((
                cryodecoder.blocks.Block_M_MBusPacket,
                cryodecoder.blocks.Block_M_MBusPacketCryoegg2023,
                cryodecoder.blocks.Block_M_MBusPacketCryowurst2023))

        # No MBus data in the top leve
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

    def getColumnValue(self, block):

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
    
class CHILBatteryVoltageColumn(L1MBusDataColumn):
    L1_class = cryodecoder.blocks.Block_C_CHIL
    def getDataValuePre2026(self, block):
        return f"{block.voltage_battery.value}"
    def getDataValue(self, block):
        return f"{block.voltage_battery.value}"
    
class CHILConductivityColumn(L1MBusDataColumn):
    L1_class = cryodecoder.blocks.Block_C_CHIL
    def getDataValuePre2026(self, block):
        return f"{block.conductivity.value}"
    def getDataValue(self, block):
        return f"{block.conductivity.value}"
    
class CHILTemperatureColumn(L1MBusDataColumn):
    L1_class = cryodecoder.blocks.Block_C_CHIL
    def getDataValuePre2026(self, block):
        return f"{block.temperature_pt1000.value}"
    def getDataValue(self, block):
        return f"{block.temperature_tmp117.convertedValue:.7f}"
        
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
        
class KellerPressureColumn(L1MBusDataColumn):
    L1_class = cryodecoder.blocks.Block_K_Keller
    def getDataValue(self, block):
        return f"{block.pressure.convertedValue:.4f}"
        
class KellerTemperatureColumn(L1MBusDataColumn):
    L1_class = cryodecoder.blocks.Block_K_Keller
    def getDataValue(self, block):
        return f"{block.temperature.convertedValue:.4f}"
    
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
        
class HexColumn(DataColumn):

    def getColumnValue(self, block):
        return block.to_bytes().hex()

class LoggerBase:
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

        self._csv_logger = logging.getLogger("cryodecoder.data")
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

    def __init__(self, port="COM1", baud_rate=19200, file_root : Union[NoneType,PathLike] = None):

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

        self._serial = serial.Serial(port, baud_rate)
        self._parser = Parser()

        # Setup logging
        self.__setup_loggers()
       
    def getRoot(self):

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

        return self.getRoot() / f"data_{self._init_time.strftime("%Y%m%d_%H%M%S")}.csv"

    def getLoggerFilename(self):

        return self.getRoot() / f"logger_{self._init_time.strftime("%Y%m%d_%H%M%S")}.log"

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

        # Assign logging objects to the decoder
        self.output_logger = dl_logger
        self.output_console = cmd_logger

    def run(self):

        print("Running decoder...")
        # self._serial.open()

        while True:
            try:
                byte = self._serial.read(1)
                while ((byte != b'') or not self._parser.complete()):
                    if (byte == b'#'):
                        # Read until end of line
                        decode_message = ""
                        byte = self._serial.read(1)
                        while (byte != b'\n' and byte != b'\r'):
                            decode_message += byte.decode("ascii")
                            byte = self._serial.read(1)
                        byte = self._serial.read(1)
                        self.output_logger.log(logging.INFO, decode_message)
                    else:
                        # print(f"{byte.hex()} -> {byte.decode("ascii") if byte[0] < 128 and byte[0] > 32 else f"({byte[0]})"}")
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
        
    def save(self):
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

    def __init__(self, input_file, output_file):

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

    parser = argparse.ArgumentParser(
            prog='parser.py',
            description='Runs a file-based or Serial decoder for Cryoegg packets.',
            epilog='See [URL] for more help.'
        )
    
    parser.add_argument("type", choices=["serial", "file"]
                        )
    parser.add_argument("-p", "--port", type=str, required=False, default="COM1")
    parser.add_argument("-b", "--baud", type=int, required=False, default=19200)

    # Input and output files
    parser.add_argument("-i", "--input", type=str, required=False, default="")
    parser.add_argument("-o", "--output", type=str, required=False, default="")

    args = parser.parse_args()

    if args.type == "serial":

        print(f"Starting serial decoder with port {args.port}")

        serialDecoder = SerialDecoder(port=args.port, baud_rate=args.baud)
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