from cryodecoder.parser import Parser

def parse_hex(hex_input : str):
    """
    Parse CHIL data from hexadecimal strings.

    :param hex_input: String encoding binary data in CHIL format.
    :return: Ordered list of the decoded blocks from the string
    :rtype: list[cryodecoder.blocks.Block]
    
    """
    # Create a parser object
    parser = Parser()
    parser.push(bytes.fromhex(hex_input))

    # Run the parser
    while not parser.complete():
        parser.update()

    # Return the parsed blocks
    #   ...because we're parsing from a string we don't care about the 
    #   timestamp that comes from the Parser object so we can do some 
    #   reformating...
    return [block for timestamp, block in parser._blocks]