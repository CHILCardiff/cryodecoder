import pytest

import cryodecoder
import cryodecoder.blocks
import cryodecoder.exceptions

###############################################################################
# Test fields
###############################################################################
def test_invalid_field():

    class GenericField(cryodecoder.blocks.Field):
        def to_bytes(self):
            pass
        def from_bytes(self):
            pass

    generic_field = GenericField(0, 1)
    with pytest.raises(TypeError): 
        generic_field.raw = 0 # Assign a value that is not of type bytes
    with pytest.raises(ValueError):
        generic_field.raw = b'\x00\x00' # Assign bytes longer than the field

###############################################################################
# Test Payload field 
###############################################################################
def test_payload_access():

    payload = cryodecoder.blocks.Payload(0)
    # Test conversion of Paylaod is prevented
    with pytest.raises(cryodecoder.exceptions.PayloadAccessError):
        payload.to_bytes(b'')
    with pytest.raises(cryodecoder.exceptions.PayloadAccessError):
        payload.from_bytes(b'')
    # Test assignment to Payload is prevented
    with pytest.raises(cryodecoder.exceptions.PayloadAccessError):
        payload.value = b''
    with pytest.raises(cryodecoder.exceptions.PayloadAccessError):
        payload.raw = b''

def test_field_byte_order():

    # Valid values
    for value in ("little", "big"):
        ui = cryodecoder.blocks.UnsignedIntField(0, 2, byte_order=value)
        assert ui.byte_order == value
        
    # Try invalid values
    with pytest.raises(ValueError):
        ui = cryodecoder.blocks.UnsignedIntField(0, 2, byte_order="invalid")

    # Invalid field order
    with pytest.raises(ValueError):
        ui = cryodecoder.blocks.UnsignedIntField(field_order=-1, byte_width=1)
    
    # Invalid byte width
    with pytest.raises(ValueError):
        ui = cryodecoder.blocks.UnsignedIntField(field_order=0, byte_width=-1)

def test_field_IEEE754float():

    # Create a reasonable float (conditioned for IEEE 754)
    float_value = 1.1295252
    error = 1e-7
    binary_value = b'\x48\x94\x90\x3f'

    ieee754float = cryodecoder.blocks.IEEE754Float(field_order=0)
    ieee754float.value = float_value

    # Check forward/backward conversion
    assert ieee754float.to_bytes(ieee754float.value) == binary_value
    assert abs(ieee754float.from_bytes(binary_value) - float_value) < error

def test_field_TemperatureTMP117Field():

    field = cryodecoder.blocks.TemperatureTMP117Field(field_order=0)
    value = -10
    temperature = value * 0.0078125

    field.value = value
    assert field.convertedValue == temperature
    field.convertedValue = 0.0078125 * -20
    assert field.value == -20

def test_field_TemperatureSHT30Field():

    field = cryodecoder.blocks.TemperatureSHT30Field(field_order=0)
    value = 1234
    convertedValue = -45 + 175 * value / (2**16 - 1)

    field.value = value
    assert field.convertedValue == convertedValue

    field.convertedValue = -33.4615091
    value = 4321
    assert field.value == value

def test_field_RelativeHumiditySHT30Field():

    field = cryodecoder.blocks.RelativeHumiditySHT30Field(field_order=0)
    value = 1234
    convertedValue = 100 * value / (2**16 - 1)

    field.value = value
    assert field.convertedValue == convertedValue

    value = 4321
    field.convertedValue = 100 * value / (2**16 - 1)
    assert field.value == value

def test_field_TemperatureKellerField():

    field = cryodecoder.blocks.TemperatureKellerField(field_order=0)

    value = 1234
    convertedValue = ((value / 16) - 24) * 0.05 - 50.0
    field.value = value
    assert field.convertedValue == convertedValue

    value = 4321
    convertedValue = ((value / 16) - 24) * 0.05 - 50.0
    field.convertedValue = convertedValue
    assert field.value == value

def test_field_PressureKellerField():

    field = cryodecoder.blocks.PressureKellerField(field_order=0)
    value = 20000

    convert_pressure = lambda value, p_min, p_max : (value - 16384) / 32768 * (p_max - p_min) + 1 

    with pytest.raises(cryodecoder.exceptions.MissingPressureBounds):
        field.value = 10
        assert field.convertedValue == convert_pressure(value, 0, 0)

    # Create a new field
    field = cryodecoder.blocks.PressureKellerField(field_order=0, pressure_min=0, pressure_max=30.0)
    field.value = value
    assert field.convertedValue == convert_pressure(value, 0, 30.0)

    # Assign the converted value
    value = 30000
    converted_value = convert_pressure(value, 0, 30.0)
    field.convertedValue = converted_value
    assert field.value == value

###############################################################################
# Test block
###############################################################################

def test_block_instance_variables():

    class TestBlock(cryodecoder.blocks.Block):
        field = cryodecoder.blocks.UnsignedIntField(0, 1)

    blockA = TestBlock()
    blockB = TestBlock()

    assert blockA != blockB

def test_block_field_checking():

    # Try to create a block with identical field orders
    class InvalidBlock(cryodecoder.blocks.Block):
        fieldA = cryodecoder.blocks.UnsignedIntField(0, 1)
        fieldB = cryodecoder.blocks.UnsignedIntField(0, 1)

    with pytest.raises(ValueError):
        block = InvalidBlock()

def test_create_L1_block():

    # Create L1 block
    l1_block = cryodecoder.blocks.Block_C_CHIL(
        sequence_number    = 120,
        voltage_battery    = 3890,
        conductivity       = 1234,
        temperature_tmp117 = 3200
    )

    # Check values
    assert l1_block.sequence_number.value    == 120
    assert l1_block.voltage_battery.value    == 3890
    assert l1_block.conductivity.value       == 1234
    assert l1_block.temperature_tmp117.value == 3200

    # Convert to bytes
    raw = l1_block.to_bytes()

    assert raw == b'C\x07\x78\x32\x0F\xD2\x04\x80\x0c'

    # Do the same, but assign some values with raw values
    l1_block_semiraw = cryodecoder.blocks.Block_C_CHIL(
        sequence_number    = b'\x13',
        voltage_battery    = 3890,
        conductivity       = 1234,
        temperature_tmp117 = b'\x22\x33'
    )

    assert l1_block_semiraw.sequence_number.raw    == b'\x13'
    assert l1_block_semiraw.temperature_tmp117.raw == b'\x22\x33'

    # Create block with empty initialisiation

    l1_block_empty = cryodecoder.blocks.Block_C_CHIL()

    assert l1_block_empty.to_bytes() == (b'C\x07' + b'\00' * 7)

def test_concat_blocks():

    c_block = cryodecoder.blocks.Block_C_CHIL()
    a_block = cryodecoder.blocks.Block_A_LSM303()

    # Check commutivity of lengths 
    assert len(c_block.to_bytes() + a_block.to_bytes()) == len(c_block) + len(a_block)

def test_l2_block_creation():
    
    test_payload = b'my_payload'

    mbus_block = cryodecoder.blocks.Block_M_MBusPacket(
        channel_number = 0,
        c_field = 0x44,
        m_field = b'\x47\x48',
        uid = 0xCE241234,
        version = 1,
        device = 7,
        ci_field = 0x44,
        rssi = 50
    )
    
    # Check that we can represent the total block length correctly
    len_mbus_block = 12 + 2 # Body + header + payload
    assert len(mbus_block) == len_mbus_block

    # Create a child block
    l1_block = cryodecoder.blocks.Block_C_CHIL(
        sequence_number    = 120,
        voltage_battery    = 3890,
        conductivity       = 1234,
        temperature_tmp117 = 3200
    )
    len_l1_block = 9
    assert len(l1_block) == len(l1_block)

    # Add it to the mbus block
    mbus_block.add_child(l1_block)

    assert len(mbus_block) == len_l1_block + len_mbus_block

    # Add another block
    l1_block_b = cryodecoder.blocks.Block_B_BMA400(
        acc_x = 999,
        acc_y = 9001,
        acc_z = -300, 
    )

    len_l1_block_b = 8
    assert len(l1_block_b) == 8

    mbus_block.add_child(l1_block_b)

    assert len(mbus_block) == len_l1_block + len_l1_block_b + len_mbus_block 

    assert len(mbus_block) == len(mbus_block.to_bytes())

    assert mbus_block.calculate_block_length() == len_l1_block + len_l1_block_b + 12 # 12 for mbus header length

def test_l2_receiver_block():
    
    test_payload = b'my_payload'

    r_block = cryodecoder.blocks.Block_R_Receiver()
    
    # Create a child block
    l1_block = cryodecoder.blocks.Block_C_CHIL(
        sequence_number    = 120,
        voltage_battery    = 3890,
        conductivity       = 1234,
        temperature_tmp117 = 3200
    )

    len_l1_block = 9
    assert len(l1_block) == len(l1_block)

    # Add it to the mbus block
    r_block.add_child(l1_block)

    assert len(r_block) == len(l1_block) + r_block.header.length()

def test_l2_block_payload_access():

    test_payload = b'my_payload'

    with pytest.raises(cryodecoder.exceptions.PayloadAccessError):
        mbus_block = cryodecoder.blocks.Block_M_MBusPacket(
            channel_number = 0,
            c_field = 0x44,
            m_field = b'\x47\x48',
            uid = 0xCE241234,
            version = 1,
            device = 7,
            ci_field = 0x44,
            rssi = 50,
            payload = test_payload
        )

    mbus_block = cryodecoder.blocks.Block_M_MBusPacket(
        channel_number = 0,
        c_field = 0x44,
        m_field = b'\x47\x48',
        uid = 0xCE241234,
        version = 1,
        device = 7,
        ci_field = 0x44,
        rssi = 50,
    )
    with pytest.raises(cryodecoder.exceptions.PayloadAccessError):
        mbus_block.payload.raw = 10

def test_l3_multi_payload():

    d_block = cryodecoder.blocks.Block_D_Datalogger(
        receiver_id = b'TEST',
        timestamp = 1780420334,
        sequence_number = b'\x99'
    )

    mbus_block = cryodecoder.blocks.Block_M_MBusPacket(
        channel_number = 0,
        c_field = 0x44,
        m_field = b'\x47\x48',
        uid = 0xCE241234,
        version = 1,
        device = 7,
        ci_field = 0x44,
        rssi = b'\xff'
    )

    # Create a child block
    l1_block = cryodecoder.blocks.Block_C_CHIL(
        sequence_number    = 120,
        voltage_battery    = 3890,
        conductivity       = 1234,
        temperature_tmp117 = 3200
    )

    mbus_block.add_child(l1_block)
    d_block.add_child(mbus_block)

    assert (len(d_block.to_bytes()) ==  
        d_block.header.length() + 
        d_block.count_field_bytes() +
        mbus_block.header.length() + 
        mbus_block.count_field_bytes() +
        l1_block.header.length() + 
        l1_block.count_field_bytes())

@pytest.mark.parametrize("header,num_bytes", (
    ((b"W1", 52), (b"W2", 58), (b"C0", 23), (b"C1", 38))
))
def test_BlockHeaderLegacy_valid(header, num_bytes):

    block_header = cryodecoder.blocks.BlockHeaderLegacy()
    # Annoying Python functionality here where a singular index (i.e. [0])
    # casts the value to an int. Hence, array-like index with length 1
    # (i.e. [0:1]) keeps the type as bytes.
    assert block_header.get_bytes_remaining(header[0:1], header[1:2]) == num_bytes