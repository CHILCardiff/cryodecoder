import pytest

import cryodecoder
import cryodecoder.blocks
import cryodecoder.parser

import io

def test_parser_from_bytestream():

    raw_stream = io.BytesIO(bytes.fromhex("446500000000005d0e1f6a005226450c1aa47b442a68c2413a655e85560e017000000000000000005816b0324206c00080ff80424d32024424489b0025ce0107aa4307002f107c0f880c410ce8fe0eff6d004aff0fffadbf4b0dfa3f005e01a969000000007a00a2"))

    # Define parser object
    parser = cryodecoder.parser.Parser()

    byte = raw_stream.read(1)
    while (byte != b'' or not parser.complete()):
        parser.push(byte)
        parser.update()
        byte = raw_stream.read()

    # Check we have a Datalogger block
    assert parser.available() == 1
    
    block = parser.read()
    assert isinstance(block, cryodecoder.blocks.Block_D_Datalogger)

def test_parser_from_file_eggonly():

    # Define parser object
    parser = cryodecoder.parser.Parser()

    with open("data/childata_cryoeggonly.log", "rb") as fh:

        byte = fh.read(1)
        while (byte != b'' or not parser.complete()):
            parser.push(byte)
            parser.update()
            byte = fh.read(1)

    # Check we have a Datalogger block
    assert parser.available() == 3

    while parser.available():
        
        block = parser.read()
        assert isinstance(block, cryodecoder.blocks.Block_D_Datalogger)
        
def test_parser_from_file_mixed():

    # Define parser object
    parser = cryodecoder.parser.Parser()

    with open("data/childata_eggwurst_20260602.log", "rb") as fh:

        byte = fh.read(1)
        while (byte != b'' or not parser.complete()):
            parser.push(byte)
            parser.update()
            byte = fh.read(1)

    # Check we have a Datalogger block
    assert parser.available() == 10

    cryoegg_blocks = 0
    cryowurst_blocks = 0

    while parser.available():

        block = parser.read()
        assert isinstance(block, cryodecoder.blocks.Block_D_Datalogger)
        assert block.hasChild(cryodecoder.blocks.Block_M_MBusPacket)

        if block.hasChild(cryodecoder.blocks.Block_M_MBusPacket):

            mbus_block = block.getChild(cryodecoder.blocks.Block_M_MBusPacket)
            if mbus_block.hasChild(cryodecoder.blocks.Block_C_CHIL):

                chil_block = mbus_block.getChild(cryodecoder.blocks.Block_C_CHIL)

                # Temperature
                print(f"Temperature     (value): {chil_block.temperature_tmp117.value}")
                print(f"Temperature (converted): {chil_block.temperature_tmp117.convertedValue}")

        if block.children[1].uid.value & 0xff == 0xce:
            cryoegg_blocks += 1
        elif block.children[1].uid.value == 0x78563412:
            cryowurst_blocks += 1
        else:
            raise ValueError(f"Invalid uid: {block.children[1].uid.value:x}")
        
    assert cryoegg_blocks == 6
    assert cryowurst_blocks == 4