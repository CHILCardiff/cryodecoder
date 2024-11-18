import toml
import datetime

#load in info from packets.toml
with open('packets.toml', 'r') as f:
    packets= toml.load(f)

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
    def get_receiver_packet():
        pass
    def get_instrument_packet():
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
    def get_identifier():
        """returns packet type identifier (i.e. C1/W2/etc.)"""
        pass

class CryoeggPacket(InstrumentPacket):
    """
    to match cryoegg_raw_table

    exposes raw data as named attributes, with correct endianness/conversion
    i.e.:

        packet = CryoeggPacket()
        print(packet.temperature)
        print(packet.rssi)

    """
    pass

class CryowurstPacket(InstrumentPacket):
    """
    to match cryowurst_raw_table
    """
    pass

class ReceiverPacket:
    """implements datalogger/receiver data class
    to match receiver_data_table"""
    pass
