from abc import abstractmethod
from base64 import b64decode
from dataclasses import dataclass
import datetime
import os
import cryodecoder
import struct
import sys
from types import NoneType
import typing
from typing import Union
import yaml

if sys.version_info[1] > 11:
    import importlib.resources as importlib_resources
else:
    import importlib_resources as importlib_resources

#region load in info from packets.toml

# Create empty packets object
packets = None

# Import packets definition
#source = importlib.resources.files(__package__).joinpath("packets.toml") 
source = importlib_resources.files(cryodecoder).joinpath("packets.yml") 
with importlib_resources.as_file(source) as packet_config_path:
    with open(packet_config_path, "r") as fh:
        packets = yaml.safe_load(fh)
    
# And finally check that we've actually imported something
if packets == None:
    raise FileNotFoundError("Could not load packets.yaml")

packet_types_string = list(packets['InstrumentType'].keys())
packet_types_bytes = [bytes(item, encoding='utf-8') for item in packet_types_string]
#endregion

def bytes_to_packets(byte_array):
    """
    returns a list of SDPackets from a byte array
    """
    # Rewritten as while loop
    sd_packets = []
    # store current position in array
    cursor = 0
    found_start = False

    while cursor < len(byte_array) - 1:
        # safe to iterate over length - 1 as we can't have a 1-byte packet
        # so instead this saves checking that we have enough of the array
        # left to do the type comparison
        found_start = False    
        # Iterate over packet types
        for type_bytes, type_string in zip(packet_types_bytes, packet_types_string):
            
            if byte_array[cursor : cursor + 2] == type_bytes:
                # Try creating the packet
                length = packets["InstrumentType"][type_string]["length"]
                packet = SDPacket(byte_array[cursor : cursor + length])
                sd_packets.append(packet)
                # increment cursor position to skip packet
                cursor = cursor + length
                # Set found_start flag to true
                found_start = True
                # quit checking other packet types
                break
        
        # If we haven't found any packets, increment by one to keep searching
        if not found_start:
            cursor = cursor + 1
        
    # Return all the SDPackets we have found
    return sd_packets  
    
def parse(input : typing.Union[bytes, bytearray, str], mode : typing.Literal["bytes", "hex", "base64"] = "bytes", encoding : str = "ascii"): 
    """
    returns a single packet or list of packets from a byte or string
    input
    """
    if mode == "bytes":
        if type(input) is str:
            return bytes_to_packets(bytearray(input, encoding=encoding))
        else:
            return bytes_to_packets(input)
    else:
        if type(input) is not str:
            raise TypeError(f"Input should be type 'str' in parsing mode '{mode}'")
        if mode == "hex":
            # Convert hex string to byte array
            return bytes_to_packets(bytes.fromhex(input))
        elif mode == "base64":
            # Convert base64 string to byte array
            return bytes_to_packets(b64decode(input))
        else:
            raise ValueError(f"Invalid parsing mode '{mode}'.")

# Instrument packets
class InstrumentPacket:
    @abstractmethod
    def get_identifier(self) -> str:
        """returns packet type identifier (i.e. C1/W2/etc.)"""
        pass

@dataclass
class CryoeggPacket(InstrumentPacket):

    """
    to match cryoegg_raw_table

    exposes raw data as named attributes, with correct endianness/conversion
    i.e.:

        packet = CryoeggPacket()
        print(packet.temperature)
        print(packet.rssi)

    """
    instrument_id           : int
    conductivity_raw        : int
    temperature_pt1000_raw  : int
    pressure_raw            : int
    temperature_raw         : int
    battery_voltage         : int
    sequence_number         : int
    rssi                    : float
    packet_type          : str
    # Database-only: generated when retrieving from cryodb
    cryoegg_raw_id      : Union[int, NoneType] = None
    receiver_data_id    : Union[int, NoneType] = None
    ingest_id           : Union[int, NoneType] = None
    
    # Implement get_identifier from packet_type
    def get_identifier(self):
        return self.packet_type
        

@dataclass
class CryowurstPacket(InstrumentPacket):
    """
    to match cryowurst_raw_table
    """
    # ([\w\d_]+)\s+INTEGER,
    instrument_id           : int
    temperature_tmp117_raw  : int
    mag_x_raw               : int
    mag_y_raw               : int
    mag_z_raw               : int
    accel_imu_x_raw         : int
    accel_imu_y_raw         : int
    accel_imu_z_raw         : int
    accel_tilt_x_raw        : int
    accel_tilt_y_raw        : int
    accel_tilt_z_raw        : int
    pitch_raw               : int
    roll_raw                : int
    conductivity_raw        : int
    pressure_raw            : int
    temperature_keller_raw  : int
    battery_voltage         : int
    sequence_number         : int
    rssi                    : float
    packet_type: str 
    # Database-only: generated when retrieving from cryodb
    receiver_data_id    : int = None
    ingest_id           : int = None

    def get_identifier(self) -> str:
        return self.packet_type
        

@dataclass
class ReceiverPacket:
    """implements datalogger/receiver data class
    to match receiver_data_table
    
    example usage:
    .. code::

        packet = ReceiverPacket(
            timestamp = datetime.datetime.now(),
            channel = 2,
            temperature = -5.2,
            pressure = 968.0,
            voltage = 12.3
        )

    """
    timestamp   : datetime.datetime
    channel     : int
    temperature : float
    pressure    : float
    voltage     : float
    # Database-only: generated when retrieving from cryodb
    receiver_data_id : int = None
    receiver_id      : int = None
    ingest_id        : int = None  

class DataPacket:
    """abstract/interface class for packet methods"""
    def __init__(self, raw_data : Union[bytes, bytearray]):
        # Validate the data type here too, rather than relying soley on typing
        if type(raw_data) not in (bytes, bytearray):
            raise TypeError(f"Packet data should be of type 'bytes' or 'bytearray' instead of {type(raw_data)}.")
        
        # Assign the raw data
        self.raw_data = raw_data
        # and strip the packet type from the data
        # TODO: is this okay to keep as bytes, or should it be converted to
        # a string?
        if self.raw_data[0:2] in packet_types_bytes:
            self.packet_type = self.raw_data[0:2]
        else:
            print('This isn\'t a packet type I recognise...')

class SDPacket(DataPacket):
    def __eq__(self, comparison):
        # Assuming the underlying raw data is equal, the packets are the same
        if type(comparison) is self.__class__:
            return self.get_raw() == comparison.get_raw()
        else:
            return False

    def get_raw(self):
        """returns raw data of complete SDPacket
        """
        return self.raw_data
    
    def get_receiver_packet(self) -> ReceiverPacket:
        """extracts and decodes receiver packet for SD packet"""
        receiver_packet_start = 2  #skips the packet type
        receiver_packet_end = packets['InstrumentType'][self.packet_type.decode('utf-8')]['instrument_packet_start']
        # Get raw bytes for receiver packet
        receiver_packet_raw=self.raw_data[receiver_packet_start:receiver_packet_end]
        # create receiver packet
        packet_info=packets['ReceiverPacket']
        timestamp_unix = int.from_bytes(receiver_packet_raw[packet_info['timestamp']['start_index']:packet_info['timestamp']['end_index']+1], 
                                    byteorder='little')
        timestamp=datetime.datetime.fromtimestamp(timestamp_unix)
        voltage = int.from_bytes(receiver_packet_raw[packet_info['logger_voltage']['start_index']:packet_info['logger_voltage']['end_index']+1],
                                   byteorder='little')
        [temperature] = struct.unpack('<f',receiver_packet_raw[packet_info['logger_temp']['start_index']:packet_info['logger_temp']['end_index']+1]) 
#            pressure= struct.unpack('f',receiver_packet_raw[packet_info['logger_pressure']['start_index']:packet_info['logger_pressure']['end_index']+1]) 
        [pressure]= struct.unpack('<f',receiver_packet_raw[packet_info['logger_pressure']['start_index']:packet_info['logger_pressure']['end_index']+1])
        channel= int.from_bytes(receiver_packet_raw[packet_info['channel_number']['start_index']:packet_info['channel_number']['end_index']+1], 
                                    byteorder = 'little', signed=False)
        receiver_packet = ReceiverPacket(timestamp=timestamp,
                                         voltage=voltage,
                                         temperature=temperature,
                                         pressure=pressure,
                                         channel=channel
        )
        return receiver_packet

    def get_instrument_packet(self) -> InstrumentPacket:
        """implements instrument packet for SD packet"""
        #work in progress
        packet_start = packets['InstrumentType'][self.packet_type.decode('utf-8')]['instrument_packet_start']
        packet_end = packets['InstrumentType'][self.packet_type.decode('utf-8')]['instrument_packet_length']+packet_start
        instrument_packet = self.raw_data[packet_start:packet_end]
        #check which packet type we have, and then decode accordingly 
        if self.packet_type==b'C1':
            packet_info = packets['CryoeggPacket']
            instrument_id=int.from_bytes(instrument_packet[packet_info['user_id']['start_index']:packet_info['user_id']['end_index']+1],
                                        byteorder = 'little', signed=False)
            conductivity_raw=int.from_bytes(instrument_packet[packet_info['conductivity']['start_index']:packet_info['conductivity']['end_index']],
                                        byteorder = 'little', signed=False)
            temperature_pt1000_raw = int.from_bytes(instrument_packet[packet_info['temperature_pt1000']['start_index']:packet_info['temperature_pt1000']['end_index']+1],
                                        byteorder = 'little', signed=True)
            pressure_raw = int.from_bytes(instrument_packet[packet_info['pressure']['start_index']:packet_info['pressure']['end_index']+1],
                                        byteorder = 'little', signed=False)
            temperature_raw = int.from_bytes(instrument_packet[packet_info['temperature']['start_index']:packet_info['temperature']['end_index']+1],
                                        byteorder = 'little', signed=True)
            battery_voltage = int.from_bytes(instrument_packet[packet_info['battery_voltage']['start_index']:packet_info['battery_voltage']['end_index']+1], byteorder = 'little', signed=True)
            sequence_number = int.from_bytes(instrument_packet[packet_info['sequence_number']['start_index']:packet_info['sequence_number']['end_index']+1],
                                        byteorder = 'little', signed=False)
            rssi = int.from_bytes(instrument_packet[packet_info['rssi']['start_index']:packet_info['rssi']['end_index']+1],
                                        byteorder = 'little', signed=False)
            packet_type=self.packet_type
            return CryoeggPacket(instrument_id=instrument_id,
                                 conductivity_raw=conductivity_raw,
                                 temperature_pt1000_raw=temperature_pt1000_raw,
                                 pressure_raw=pressure_raw,
                                 temperature_raw=temperature_raw, 
                                 battery_voltage=battery_voltage,
                                 sequence_number=sequence_number,
                                 rssi=rssi,
                                 packet_type=packet_type
                                 )
        elif self.packet_type == b'W2':
            packet_info = packets['CryowurstPacket']
            instrument_id=int.from_bytes(instrument_packet[packet_info['user_id']['start_index']:packet_info['user_id']['end_index']+1],
                                        byteorder = 'little', signed=False)
            temperature_tmp117_raw=int.from_bytes(instrument_packet[packet_info['temperature']['start_index']:packet_info['temperature']['end_index']+1],
                                         byteorder = 'little', signed=True)
            mag_x_raw=int.from_bytes(instrument_packet[packet_info['magnetometer_x']['start_index']:packet_info['magnetometer_x']['end_index']+1],
                                         byteorder = 'little', signed=True)
            mag_y_raw=int.from_bytes(instrument_packet[packet_info['magnetometer_y']['start_index']:packet_info['magnetometer_y']['end_index']+1],
                                         byteorder = 'little', signed=True)
            mag_z_raw=int.from_bytes(instrument_packet[packet_info['magnetometer_z']['start_index']:packet_info['magnetometer_z']['end_index']+1],
                                         byteorder = 'little', signed=True)
            accel_imu_x_raw=int.from_bytes(instrument_packet[packet_info['accelerometer_x']['start_index']:packet_info['accelerometer_x']['end_index']+1],
                                         byteorder = 'little', signed=True)
            accel_imu_y_raw=int.from_bytes(instrument_packet[packet_info['accelerometer_y']['start_index']:packet_info['accelerometer_y']['end_index']+1],
                                         byteorder = 'little', signed=True)
            accel_imu_z_raw=int.from_bytes(instrument_packet[packet_info['accelerometer_z']['start_index']:packet_info['accelerometer_z']['end_index']+1],
                                         byteorder = 'little', signed=True)
            accel_tilt_x_raw=int.from_bytes(instrument_packet[packet_info['tilt_x']['start_index']:packet_info['tilt_x']['end_index']+1],
                                         byteorder = 'little', signed=True)
            accel_tilt_y_raw=int.from_bytes(instrument_packet[packet_info['tilt_y']['start_index']:packet_info['tilt_y']['end_index']+1],
                                         byteorder = 'little', signed=True)
            accel_tilt_z_raw=int.from_bytes(instrument_packet[packet_info['tilt_z']['start_index']:packet_info['tilt_z']['end_index']+1],
                                         byteorder = 'little', signed=True)
            pitch_raw=int.from_bytes(instrument_packet[packet_info['pitch_x']['start_index']:packet_info['pitch_x']['end_index']+1],
                                         byteorder = 'little', signed=True)
            roll_raw=int.from_bytes(instrument_packet[packet_info['roll_y']['start_index']:packet_info['roll_y']['end_index']+1],
                                         byteorder = 'little', signed=True)
            conductivity_raw=int.from_bytes(instrument_packet[packet_info['conductivity']['start_index']:packet_info['conductivity']['end_index']],
                                        byteorder = 'little', signed=False)
            pressure_raw = int.from_bytes(instrument_packet[packet_info['pressure']['start_index']:packet_info['pressure']['end_index']+1],
                                        byteorder = 'little', signed=False)
            temperature_keller_raw = int.from_bytes(instrument_packet[packet_info['keller_temperature']['start_index']:packet_info['keller_temperature']['end_index']+1],
                                        byteorder = 'little', signed=True)
            battery_voltage = int.from_bytes(instrument_packet[packet_info['battery_voltage']['start_index']:packet_info['battery_voltage']['end_index']+1], byteorder = 'little', signed=True)
            sequence_number = int.from_bytes(instrument_packet[packet_info['sequence_number']['start_index']:packet_info['sequence_number']['end_index']+1],
                                        byteorder = 'little', signed=True)
            rssi = int.from_bytes(instrument_packet[packet_info['rssi']['start_index']:packet_info['rssi']['end_index']+1],
                                        byteorder = 'little', signed=False)
            packet_type=self.packet_type
            return CryowurstPacket(instrument_id=instrument_id,
                                    temperature_tmp117_raw=temperature_tmp117_raw,
                                    mag_x_raw=mag_x_raw,
                                    mag_y_raw=mag_y_raw,
                                    mag_z_raw=mag_z_raw,
                                    accel_imu_x_raw=accel_imu_x_raw,
                                    accel_imu_y_raw=accel_imu_y_raw,
                                    accel_imu_z_raw=accel_imu_z_raw,
                                    accel_tilt_x_raw=accel_tilt_x_raw,
                                    accel_tilt_y_raw=accel_tilt_y_raw,
                                    accel_tilt_z_raw=accel_tilt_z_raw,
                                    pitch_raw=pitch_raw,
                                    roll_raw=roll_raw,
                                    conductivity_raw=conductivity_raw,
                                    pressure_raw=pressure_raw,
                                    temperature_keller_raw=temperature_keller_raw,
                                    battery_voltage=battery_voltage,
                                    sequence_number=sequence_number,
                                    rssi=rssi,
                                    packet_type=packet_type
                                    )



class LingoMOPacket:

    def get_lingomo_id():
        pass
    def get_timestamp():
        pass

    def get_sd_packets():
        """calls bytes_to_packets on payload/message"""
        pass

class LocalPacket(DataPacket):
    def get_receiver_packet():
        """implements receiver packet for local packet"""
        pass
    def get_instrument_packet():
        """implements instrument packet for local packet"""
        pass
