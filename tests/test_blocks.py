import pytest

import cryodecoder
import cryodecoder.blocks
import cryodecoder.exceptions

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

    assert mbus_block.header.calculate_block_length(mbus_block) == len_l1_block + len_l1_block_b + 12 # 12 for mbus header length

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