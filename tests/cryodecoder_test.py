# tests to run on sample data to check all is running smoothly!
from cryodecoder import *
import datetime
import toml
import os

#region import test data
packets_source = importlib.resources.files(cryodecoder).joinpath("packets.toml") 
with importlib.resources.as_file(packets_source) as packet_config_path:
    with open(packet_config_path, "r") as f:
        packets = toml.load(f)


eggtest_source = importlib.resources.files(cryodecoder).joinpath("../../tests/data/CRYOEGG_test.log") 
with  open(eggtest_source, 'rb') as test_file:
    test_egg_data = test_file.read()

wursttest_source = importlib.resources.files(cryodecoder).joinpath("../../tests/data/CWURST_test.log") 
with  open(wursttest_source, 'rb') as test_file:
    test_wurst_data = test_file.read()

test_sd_data = test_egg_data + test_wurst_data
single_egg_sd = bytes_to_packets(test_egg_data)[0]
single_wurst_sd = bytes_to_packets(test_wurst_data)[0]

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

#test that bytes_to_packets() returns all byte arrays 
def test_sd_import():
    test_output = bytes_to_packets(test_sd_data)
    for item in test_output:
        assert type(item)==bytes

#test that SDPacket class creates an object with the right identifier
def test_sdpacket_identifier():
    packet = SDPacket(single_wurst_sd)
    assert packet.packet_type in packet_types_bytes

#test if data decoded from receiver packet are reasonable values
def test_receiver_sd_data():
    packet=cryodecoder.SDPacket(single_egg_sd)
    receiver_packet = packet.get_receiver_packet()
    errors = []

    if not datetime.datetime(2017, 1, 1, 0, 0, 0) <= receiver_packet.timestamp <= datetime.datetime(2027, 1, 1, 0, 0, 0):
        errors.append("timestamp doesn't seem right")
    if not receiver_packet.channel in [1,2]:
        errors.append("channel number doesn't seem right")
    if not -50 <= receiver_packet.temperature<= 50:
        errors.append("temperature value doesn't seem right")
    if not -50 <= convert_keller_pressure(receiver_packet.pressure, 0, 30) <= 50:
        errors.append("pressure value doesn't seem right")
    if not 0 <= receiver_packet.voltage <= 10000:
        errors.append("voltage value doesn't seem right")

    # check for errors and report back
    assert not errors, "errors occured:\n{}".format("\n".join(errors))

def test_egg_decoding():
    packet=cryodecoder.SDPacket(single_egg_sd)
    egg_packet = packet.get_instrument_packet()
    errors = []

    if not '{0:x}'.format(egg_packet.instrument_id)[0:2]=='ce':
        errors.append("instrument id doesn't seem right")
    if not 0 <= egg_packet.conductivity_raw<= 3000:
        errors.append("conductivity doesn't seem right")
    if not -50 <= convert_keller_temperature(egg_packet.temperature_pt1000_raw)<= 50:
        errors.append("temperature value doesn't seem right")
    if not 3000 <= egg_packet.battery_voltage<= 4000:
        errors.append("voltage doesn't seem right")
    if not 0 <= egg_packet.sequence_number<= 256:
        errors.append("sequence number doesn't seem right")
    if not 0 <= egg_packet.rssi<= 1000:
        errors.append("rssi doesn't seem right")

    # check for errors and report back
    assert not errors, "errors occured:\n{}".format("\n".join(errors))

def test_wurst_decoding():
    packet=cryodecoder.SDPacket(single_wurst_sd)
    wurst_packet = packet.get_instrument_packet()
    errors = []

    if not '{0:x}'.format(wurst_packet.instrument_id)[0:2]=='cf':
        errors.append("instrument id doesn't seem right")
    if not -50 <= wurst_packet.temperature_tmp117_raw*0.0078125 <= 50:
        errors.append("tmp temperature value doesn't seem right")
    if not -50 <= convert_keller_temperature(wurst_packet.temperature_keller_raw) <= 50:
        errors.append("temperature value doesn't seem right")
    if not 0 <= wurst_packet.conductivity_raw<= 3000:
        errors.append("conductivity doesn't seem right")
    if not 3000 <= wurst_packet.battery_voltage<= 4000:
        errors.append("voltage doesn't seem right")
    if not 0 <= wurst_packet.sequence_number<= 256:
        errors.append("sequence number doesn't seem right")
    if not 0 <= wurst_packet.rssi<= 1000:
        errors.append("rssi doesn't seem right")

    # check for errors and report back
    assert not errors, "errors occured:\n{}".format("\n".join(errors))
