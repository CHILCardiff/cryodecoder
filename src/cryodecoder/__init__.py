from abc import abstractmethod
from dataclasses import dataclass
import toml
import datetime
import importlib.resources

#load in info from packets.toml

# JH: can't rely on "packets.toml" being on the executable path, 
#     so we need to use importlib.resources to load the TOML config

# Create empty packets object
packets = None

# Import packets definition
source = importlib.resources.files(__package__).joinpath("packets.toml") 
with importlib.resources.as_file(source) as packet_config_path:
    with open(packet_config_path, "r") as fh:
        packets = toml.load(fh)
    
# And finally check that we've actually imported something
if packets == None:
    raise ValueError("Could not load packets.toml")

packet_types_string = list(packets['InstrumentType'].keys())
packet_types_bytes = [bytes(item, encoding='utf-8') for item in packet_types_string]

def bytes_to_packets(byte_array):
    """
    returns a list of SDPackets from a byte array
    """
    sd_packets = []
    for i in range(len(byte_array)):
        for j in range(len(packet_types_bytes)):
            if byte_array[i:i+2]==packet_types_bytes[j]:
                sd_packets.append(byte_array[i:i+(packets['InstrumentType'][packet_types_string[j]]['length'])])
    return sd_packets    


class DataPacket:
    """abstract/interface class for packet methods"""
    @abstractmethod
    def get_receiver_packet(self):
        pass
    @abstractmethod
    def get_instrument_packet(self):
        pass
    @abstractmethod
    def get_raw(self):
        pass

class SDPacket(DataPacket):
    def __init__(self, raw_data):
        self.raw_data = raw_data
        if self.raw_data[0:2] in packet_types_bytes:
            self.packet_type = self.raw_data[0:2]
        else:
            print('This isn\'t a packet type I recognise...')
    def get_instrument_packet(self):
        """implements instrument packet for SD packet"""
        #work in progress
        packet_start = packets['InstrumentType'][self.packet_type.decode('utf-8')]['instrument_packet_start']
        packet_end = packets['InstrumentType'][self.packet_type.decode('utf-8')]['instrument_packet_length']+start
        instrument_packet = self.raw_data[packet_start:packet_end]
        #should do something clever with the packet types dictionary here
#        if self.packet_type==b'C1':
    def get_receiver_packet(self):
        """implements receiver packet for SD packet"""
        #work in progress
        receiver_packet_end = packets['InstrumentType'][self.packet_type.decode('utf-8')]['instrument_packet_start']
        instrument_packet_end = packets['InstrumentType'][self.packet_type.decode('utf-8')]['instrument_packet_length']+receiver_packet_end
        receiver_packet=self.raw_data[0:receiver_packet_end]+self.raw_data[instrument_packet_end:-1]
        self.header = receiver_packet[0:2].decode('utf-8')
        self.time_int = int.from_bytes(receiver_packet[2:6], byteorder='little')
        self.time_formatted = datetime.datetime.fromtimestamp(self.time_int)
#        self.logger_temp = int.from_bytes(receiver_packet[6:10], byteorder='little')
        self.solar_voltage = int.from_bytes(receiver_packet[14:16], byteorder='little')
        self.sequence_number = int.from_bytes(receiver_packet[-2:-1], byteorder='little')

    def get_raw(self):
        """returns raw data of complete SDPacket
        """
        return self.raw_data


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
    packet_version          : str
    # Database-only: generated when retrieving from cryodb
    cryoegg_raw_id      : int = None,
    receiver_data_id    : int = None
    ingest_id           : int = None
    
    # Implement get_identifier from packet_version
    def get_identifier(self):
        return self.packet_version

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
    packet_version          : str 
    # Database-only: generated when retrieving from cryodb
    receiver_data_id    : int
    ingest_id           : int

    def get_identifier(self) -> str:
        return self.packet_version

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
