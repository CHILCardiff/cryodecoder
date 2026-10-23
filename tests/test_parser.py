import pytest

import cryodecoder
import cryodecoder.blocks
import cryodecoder.parser

import io

###############################################################################
# Definitions of test packets
###############################################################################
test_packets = {
    "W1" : "573130FBD3647F678841DAAF5944EF030124440300020020CF0107AC086400A8FECE0042FFF0FDFE0359FFF8FECB0D2700000E105060",
    "W2" : "57325c2ffb661fe95841172d5d44be0d022c442448020024cf0107acf9ffde0062004a0028c0c0fde0021e00e9ff1afc1100f3ff83062d683f3f8b0d30a4",
    "W2_GROUP" : "57325c2ffb661fe95841172d5d44be0d022c442448020024cf0107acf9ffde0062004a0028c0c0fde0021e00e9ff1afc1100f3ff83062d683f3f8b0d30a457327e30fb66d7e85841332a5d44b90d022c442448040024cf0107acf2ff8000b900bdff98bfdc04a8fecdff60001ffce3ff3700e505c67e3e3e890d61b65732f12dfb66e97c5941fd385d44b20d022c442448070024cf0107acfaffde01f900efff20c084069c0069ff85002efcaaff4c008907000000008d0d30a25732392bfb66d2935c41124a5d44b40d022c442448080024cf0107acffff6601c2ff03ff6cc098f61cfee1ffaaff1dfcefffcfff7b07000000008b0d306e",
    "C1" : "4331d56e4e67cd5a04c0bd496c44ff0b0216442448010024ce0107aa690f030413724c3f550fe7c40d",
    "C1_GROUP" : "4331b8e2fa66da52d940f1526f44f20c0216442448180024ce0107aab40c030452558d3eb50f56a835433198e1fa6621b8d9405f466f44f30c0216442448200024ce0107aa170e0304e83f9a3e950fbaa600",
    "CHIL_CE" : "RGUAMVNJVM421moAUiZFDPZ0bEQf+em/AAAAAFYOaHSIO1A2aNRINlAKSDZCBkADAAcAPk0yAUQkSDIAJs4BB6tDB93KD6gN/f9BDFr/h//KAiwODwOcwksNgEMCPgDtcQAAAADIAKQ=",
    "CHIL_CW" : "447100315349545743946a005226450c4d7f6f44aec05a4100000000560e84730000000000000000000000004206c008c0f900404d3e02442448140026cf0107ab4307d70310730ce3ff410ca80088fd6d00fd000a40e6024b0d00000000030000803f000080bf540ad7ffb9ffe503e9ffd8ffc6",
    "CHIL_C1" : "",
    "CHIL_W2" : ""
}

test_packets_decoded = {
    "W2" : None,
    "W2_GROUP" : None,
    "C1" : None,
    "C1_GROUP" : None,
    "CHIL_CE" : None,
    "CHIL_CW" : None,
    "CHIL_C1" : None,
    "CHIL_W2" : None
}
###############################################################################

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
    
    time, block = parser.read()
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
        
        time, block = parser.read()
        assert isinstance(block, cryodecoder.blocks.Block_D_Datalogger)

def test_parser_from_file_mixed_formats():

    # Define parser object
    parser = cryodecoder.parser.Parser()

    with open("data/childata_mixed_packet_formats_eggonly.log", "rb") as fh:

        byte = fh.read(1)
        while (byte != b'' or not parser.complete()):
            parser.push(byte)
            parser.update()
            byte = fh.read(1)

    assert parser.available() == 36

    new_blocks = 0
    old_blocks = 0

    while parser.available():
        
        time, block = parser.read()
        if block.hasChild(cryodecoder.blocks.Block_M_MBusPacket):
            new_blocks += 1
        if block.hasChild(cryodecoder.blocks.Block_M_MBusPacketCryoegg2023):
            old_blocks += 1

    assert new_blocks == 18
    assert old_blocks == 18

        
def test_parser_from_file_mixed_instruments():

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

        time, block = parser.read()
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

# Test packets
def test_parse_hex_W1():

    blocks = cryodecoder.parse_hex(test_packets["W1"])
    assert len(blocks) == 1
    assert isinstance(blocks[0], cryodecoder.blocks.Block_W1_Wurst)

    assert f"{blocks[0].uid.value}" == "cf200020"

# Test packets
def test_parse_hex_W2():

    blocks = cryodecoder.parse_hex(test_packets["W2"])
    assert len(blocks) == 1
    assert isinstance(blocks[0], cryodecoder.blocks.Block_W_Wurst)

    assert blocks[0].uid.value

def test_parse_hex_W2GROUP():



