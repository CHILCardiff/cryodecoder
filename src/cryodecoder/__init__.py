import toml

#load in info from packets.toml
with open('packets.toml', 'r') as f:
    packets= toml.load(f)

packet_types = list(packets['InstrumentType'].keys())
packet_lengths = list(packets['InstrumentType'].items())

def bytes_to_packets(byte_array):
    """
    returns a list of SDPackets from a byte array
    """
    sd_packets = []
    for i in range(len(byte_array)):
        for j in range(len(packet_types)):
            if byte_array[i:i+2]==packet_types[j]:
                sd_packets.append(byte_array[i:i+packet_lengths][j])
    return sd_packets    

class LingoMOPacket:

    def get_lingomo_id():
        pass
    def get_timestamp():
        pass

    def get_sd_packets():
        """calls bytes_to_packets on payload/message"""
        pass

class DataPacket:
    """abstract/interface class for packet methods"""
    def get_receiver_packet():
        pass
    def get_instrument_packet():
        pass

class SDPacket(DataPacket):
    def get_receiver_packet():
        """implements receiver packet for SD packet"""
        pass
    def get_instrument_packet():
        """implements instrument packet for SD packet"""
        pass
    def get_identifier():
        """returns packet type identifier (i.e. C1/W2/etc.)"""
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
