def bytes_to_packets():
    """
    returns a list of SDPackets from a byte array
    """
    pass

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
