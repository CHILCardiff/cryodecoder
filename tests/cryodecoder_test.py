# tests to run on sample data to check all is running smoothly!
from cryodecoder import *
import datetime
import toml
import os

# # region load info from packets.toml
# with open('packets.toml', 'r') as f:
#     packets= toml.load(f)

# packet_types_string = list(packets['InstrumentType'].keys())
# packet_types_bytes = [bytes(item, encoding='utf-8') for item in packet_types_string]
# #endregion

#region import test data
packets_source = importlib.resources.files(cryodecoder).joinpath("packets.toml") 
with importlib.resources.as_file(packets_source) as packet_config_path:
    with open(packet_config_path, "r") as f:
        packets = toml.load(f)

#working_directory = os.path.dirname(os.path.abspath(__file__)) 
#test_egg_sd_file = working_directory+'/data/CRYOEGG_test.log'
#test_wurst_sd_file = working_directory+'/data/CWURST_test.log'

eggtest_source = importlib.resources.files(cryodecoder).joinpath("../../tests/data/CRYOEGG_test.log") 
with  open(eggtest_source, 'rb') as test_file:
    test_egg_data = test_file.read()

wursttest_source = importlib.resources.files(cryodecoder).joinpath("../../tests/data/CWURST_test.log") 
with  open(wursttest_source, 'rb') as test_file:
    test_wurst_data = test_file.read()

test_sd_data = test_wurst_data + test_egg_data
single_wurst_sd = bytes_to_packets(test_wurst_data)[0]
single_egg_sd = bytes_to_packets(test_egg_data)[0]

#random invalid byte string for testing
invalid_sd = b'\x8d\xad\xd3\xe4\x0f\x9d\x3e\x67\x71\x2d\x24\x96\x34\xf2\x52\xad\x59\xdb\xf0\xed\x82\x59\xe2\x16\xfd\x6a\xd8\xb5\xbb\xce\xb0\x84\x8e\x2d\x98\x9f\x1a\xe3\x8d\x7b\xb7\x8b\x1f\x17\xe6\xae\x1c\xf0\x91\xf6\x60\x74\x26\x09\xdb\xe5\x9f\x8b\x01\xe6\x13\xfb\x3b\xea\xfc\x6f\x57\x56\x27\x64\x8c\xbb\x57\x8f\x5c\x51\x7e\xb9\x73\xea\x18\xf5\xd7\xce\x1a\x94\xb9\x7e\xb9\x72\x34\x96\x56\x15\xb8\xd6\xa9\xe9\x6b\xf2\xfb\x87\xa7\xae\xed\xdb\x43\x5d\x66\xac'
#endregion

#test that bytes_to_packets() returns all byte arrays 
def test_sd_import():
    test_output = bytes_to_packets(test_sd_data)
    for item in test_output:
        assert type(item)==bytes

#test that SDPacket class creates an object with the right identifier
def test_sdpacket_identifier():
    packet = SDPacket(single_egg_sd)
    assert packet.packet_type in packet_types_bytes

#test that get_instrument_packet returns reasonable values from cryoegg packet
def test_sd_egg_decoding():
    packet = cryodecoder.SDPacket(single_egg_sd).get_instrument_packet()
    assert type(packet.conductivity_raw)==int

def test_sd_egg_receiver_decoding():
    receiver_packet = cryodecoder.SDPacket(single_egg_sd).get_receiver_packet()
    assert type(receiver_packet.voltage)==int
    
def test_sd_wurst_decoding():
    packet = cryodecoder.SDPacket(single_wurst_sd).get_instrument_packet()
    assert type(packet.temperature_tmp117_raw)==int

