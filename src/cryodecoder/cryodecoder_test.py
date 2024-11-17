# tests to run on sample data to check all is running smoothly!

import __init__

#region import test data
test_wurst_sd_file = '/home/sgllc3/cryorepos/cryodecoder/test_data/CWURST_test.log'
test_egg_sd_file = '/home/sgllc3/cryorepos/cryodecoder/test_data/CRYOEGG_test.log'

with  open(test_egg_sd_file, 'rb') as test_file:
    test_wurst_data = test_file.read()

with  open(test_wurst_sd_file, 'rb') as test_file:
    test_egg_data = test_file.read()

test_sd_data = test_wurst_data + test_egg_data
#endregion

#test that bytes_to_packets() returns all byte arrays 
def test_sd_import():
    test_output = __init__.bytes_to_packets(test_sd_data)
    for item in test_output:
        assert type(item)==bytes


            
    
