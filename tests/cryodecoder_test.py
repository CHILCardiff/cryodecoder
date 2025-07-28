# tests to run on sample data to check all is running smoothly!
from base64 import b64decode
from cryodecoder import *
import datetime
import os
import pytest
import yaml

if sys.version_info[1] > 11:
    import tomllib as toml
    import importlib.resources as importlib_resources
else:
    import toml
    import importlib_resources as importlib_resources

#region import test data
packets_source = importlib_resources.files(cryodecoder).joinpath("packets.yml") 
with importlib_resources.as_file(packets_source) as packet_config_path:
    with open(packet_config_path, "rb") as f:
        packets = yaml.safe_load(f.read())


eggtest_source = importlib_resources.files(cryodecoder).joinpath("../../tests/data/CRYOEGG_test.log") 
with open(eggtest_source, 'rb') as test_file:
    test_egg_data = test_file.read()

wursttest_source = importlib_resources.files(cryodecoder).joinpath("../../tests/data/CWURST_test.log") 
with open(wursttest_source, 'rb') as test_file:
    test_wurst_data = test_file.read()

test_sd_data = test_egg_data + test_wurst_data
# Need to ppend raw_data here as the bytes_to_packets function
# now returns SDPacket objects
single_egg_sd = bytes_to_packets(test_egg_data)[5].raw_data
single_wurst_sd = bytes_to_packets(test_wurst_data)[5].raw_data

#random invalid byte string for testing
invalid_sd = b'\x8d\xad\xd3\xe4\x0f\x9d\x3e\x67\x71\x2d\x24\x96\x34\xf2\x52\xad\x59\xdb\xf0\xed\x82\x59\xe2\x16\xfd\x6a\xd8\xb5\xbb\xce\xb0\x84\x8e\x2d\x98\x9f\x1a\xe3\x8d\x7b\xb7\x8b\x1f\x17\xe6\xae\x1c\xf0\x91\xf6\x60\x74\x26\x09\xdb\xe5\x9f\x8b\x01\xe6\x13\xfb\x3b\xea\xfc\x6f\x57\x56\x27\x64\x8c\xbb\x57\x8f\x5c\x51\x7e\xb9\x73\xea\x18\xf5\xd7\xce\x1a\x94\xb9\x7e\xb9\x72\x34\x96\x56\x15\xb8\xd6\xa9\xe9\x6b\xf2\xfb\x87\xa7\xae\xed\xdb\x43\x5d\x66\xac'
#endregion


#region converter functions to check if pressure and temp values are reasonable
def convert_keller_pressure (raw_pressure, keller_max_bar, keller_min_bar):
    # converts Keller digital values to real pressures in bar
    bar_pressure = 0.0

    pressure_range = keller_max_bar - keller_min_bar

    bar_pressure = ((raw_pressure - 16384) * (pressure_range / 32768)) + keller_min_bar

    return bar_pressure

def convert_keller_temperature (raw_temperature):
    # converts Keller digital values to real temperatures in Celcius
    # reduces precision to 12-bits as recommended by Keller

    celcius_temp = 0.0

    celcius_temp =  (((raw_temperature >> 4) - 24) * 0.05) - 50

    return celcius_temp
#endregion

#test that bytes_to_packets() returns all SDPackets 
def test_sd_import():
    test_output = bytes_to_packets(test_sd_data)
    for item in test_output:
        assert type(item)==cryodecoder.SDPacket

#test parse raw input functionality
def test_parse_single():

    # Load a single test packet
    single_packet_b64 = "QzEJF4doXwq0QPMUbUR5DAIWRCRIGAAkzgEHqvUAAwTWUJU+qA+uvoA="
    # Convert to bytes
    single_packet_bytes = b64decode(single_packet_b64)
    # and convert to hex
    single_packet_hex = single_packet_bytes.hex()

    # Start with a single Cryoegg packet to decode
    test_b64 = cryodecoder.parse(single_packet_b64, mode="base64")    
    test_bytes = cryodecoder.parse(single_packet_bytes, mode="bytes")
    test_hex = cryodecoder.parse(single_packet_hex, mode="hex")

    # Check that the three are identical
    assert test_b64 == test_bytes == test_hex

    # Try to create packets with incorrect mode
    with pytest.raises(ValueError):
        test_fail = cryodecoder.parse(single_packet_b64, mode="hex")
    
    with pytest.raises(TypeError):
        test_fail = cryodecoder.parse(single_packet_bytes, "hex")

    # Check that we have decoded an SDPacket
    assert type(test_b64[0]) is cryodecoder.SDPacket
    # ...which has a Cryoegg payload
    assert type(test_b64[0].get_instrument_packet()) is cryodecoder.CryoeggPacket

#test parse raw input functionality with multiple packets
def test_parse_multiple():

    # Load some data with multiple packes
    data = "VzKeE4do5RISQT0rX0QADQEsRCRIAgAkzwEHrPX/0QA5AOL/uL/g/ED/7//X/xr89//p/+8CVms/P4kNWboAVzIUFYdo80MOQY0hX0QBDQEsRCRIBAAkzwEHrPD/aQDiADP/XL9EBWz9wf9rACH83P89AJQBlHg+PosNisgAVzKlE4do5RISQT0rX0QADQEsRCRIBwAkzwEHrPj/4AHPAMr/nL9E/8gDmv8OAB78xv8IAOsCAAAAAIMNWpQAVzIGGIdotH4NQV8oX0T1DAEsRCRICAAkzwEHrPz/cQHh/wT/LMBQ+8T+7f/6/xn89v/9/wADAAAAAIYNWmAA"

    multi_packet_b64 = data
    multi_packet_bytes = b64decode(multi_packet_b64)
    multi_packet_hex = multi_packet_bytes.hex()

    # Start with a single Cryoegg packet to decode
    test_b64 = cryodecoder.parse(multi_packet_b64, mode="base64")    
    test_bytes = cryodecoder.parse(multi_packet_bytes, mode="bytes")
    test_hex = cryodecoder.parse(multi_packet_hex, mode="hex")

    # Check that we result in the same objects
    assert test_b64 == test_bytes == test_hex

    # Check we have the expected number of packets
    assert len(test_b64) == len(test_bytes) == len(test_hex) == 4

    # Check they are all SDPackets with Cryowurst payloads
    for packets in zip(test_b64, test_bytes, test_hex):
        for packet in packets:
            assert type(packet) == cryodecoder.SDPacket
            assert type(packet.get_instrument_packet()) == cryodecoder.CryowurstPacket


#test that SDPacket class creates an object with the right identifier
def test_sdpacket_identifier():
    packet = SDPacket(single_wurst_sd)
    assert packet.packet_type in packet_types_bytes

#test if data decoded from receiver packet are reasonable values
def test_receiver_sd_data():
    packet=cryodecoder.SDPacket(single_egg_sd)
    receiver_packet = packet.get_receiver_packet()

    # Test timestamp
    assert datetime.datetime(2017, 1, 1, 0, 0, 0) <= receiver_packet.timestamp <= datetime.datetime(2027, 1, 1, 0, 0, 0), "timestamp doesn't seem right"
    # Test receiver channel
    assert receiver_packet.channel in [1,2], "channel number doesn't seem right"
    # Test temperature
    assert -50 <= receiver_packet.temperature<= 50, "temperature value doesn't seem right"
    # Test keller pressure value
    assert -50 <= convert_keller_pressure(receiver_packet.pressure, 0, 30) <= 50, "pressure value doesn't seem right"

    assert 0 <= receiver_packet.voltage <= 10000, "voltage value doesn't seem right"

def test_egg_decoding():
    packet=cryodecoder.SDPacket(single_egg_sd)
    egg_packet = packet.get_instrument_packet()
    errors = []

    assert '{0:x}'.format(egg_packet.instrument_id)[0:2]=='ce', "instrument id doesn't seem right"
    assert 0 <= egg_packet.conductivity_raw<= 5000, "conductivity doesn't seem right"
    assert -50 <= convert_keller_temperature(egg_packet.temperature_pt1000_raw)<= 50, "temperature value doesn't seem right"
    assert 3000 <= egg_packet.battery_voltage<= 5000, "voltage doesn't seem right"
    assert 0 <= egg_packet.sequence_number<= 256, "sequence number doesn't seem right"
    assert 0 <= egg_packet.rssi<= 1000, "rssi doesn't seem right"

    # check for errors and report back
    assert not errors, "errors occured:\n{}".format("\n".join(errors))

def test_wurst_decoding():
    packet=cryodecoder.SDPacket(single_wurst_sd)
    wurst_packet = packet.get_instrument_packet()
    errors = []

    assert wurst_packet.instrument_id >> 24 == 0xCF, "instrument id doesn't seem right"
    assert -50 <= wurst_packet.temperature_tmp117_raw*0.0078125 <= 50, "tmp temperature value doesn't seem right"
    assert -50 <= convert_keller_temperature(wurst_packet.temperature_keller_raw) <= 50, "temperature value doesn't seem right"
    assert 0 <= wurst_packet.conductivity_raw<= 3000, "conductivity doesn't seem right"
    assert 3000 <= wurst_packet.battery_voltage<= 4000, "voltage doesn't seem right"
    assert 0 <= wurst_packet.sequence_number<= 256, "sequence number doesn't seem right"
    assert 0 <= wurst_packet.rssi<= 1000, "rssi doesn't seem right"

    # check for errors and report back
    assert not errors, "errors occured:\n{}".format("\n".join(errors))
