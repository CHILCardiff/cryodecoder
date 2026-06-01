import pytest

import cryodecoder
import cryodecoder.blocks

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

        c_block = cryodecoder.blocks.Block_C_CHIL(

        )