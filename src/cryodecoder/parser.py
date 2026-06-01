import cryodecoder
import cryodecoder.blocks
import cryodecoder.exceptions

from io import RawIOBase
from enum import Enum

class CryodecoderParser:
    
    def __init__(self, source : RawIOBase, stream_mode=False):
        """
        source : the origin of data input (file, serial output, etc.)
        stream : if true, expect continuous input and continue from EOF
                 if false, terminate at EOF
        """
        
        self.source = source
        self.stream_mode = False
        self.__finished = False
        self.buffer = b''
        # Assign a default state 
        self.state = CryodecoderParser.__stateBegin
        # Assign varaible for storing valid blocks
        self.blocks = []
        # Define variable indicating 

    def update(self):
        # Call the current state
        self.state(self)

    def finished(self):
        return self.__finished

    def __readToBuffer(self, size=1):
        bytes_in = self.source.read(size)
        if bytes_in != None:
            self.buffer += bytes_in
            return bytes_in
        else:
            if not self.stream_mode:
                self.complete = True
            return 0

    def __stateBegin(self):
        self.__block_identifier = ''
        self.__block_length = 0
        self.__total_length = 0

        # Define a stack object which keeps track of which level we are at
        self.__stack = []
        self.__stack_level = None

    def __stateReadBlockIdentifier(self):
        
        # Read in a new byte
        self.__readToBuffer()
        # Get current block identifier
        temp_block_identifier = self.buffer[0]

        # Check it is valid
        block_class = cryodecoder.blocks.get_block_class_from_identifier(temp_block_identifier)
        if (block_class == None):
            # Not a valid or registered identifier
            self.state = self.__statePopBuffer
            return
        
        level = cryodecoder.blocks.get_block_level_from_class(block_class)
        # If we have items in the stack, check that the new identifier is less
        # than the block level at the end of the state
        if len(self.__stack) > 0 and \
            level >= cryodecoder.blocks.get_block_level_from_class(self.__stack[-1].__class__):
            # We've failed that condition so raise an invalid packet error
            raise cryodecoder.exceptions.InvalidBlockLevel()

        # Assign temporary class
        self.__current_block_class = block_class
        
        # Move onto next step - read the length
        self.state = self.__stateReadBlockLength
        return

    def __stateReadBlockLength(self):
        
        # Check what our current class type is L3
        length = 0
        if self.__current_block_class == cryodecoder.blocks.L3ContextBlock:
            if (self.__total_length < 3):
                 # if so, read in enough data that we have 3 bytes in the buffer
                self.__readToBuffer(3 - self.__total_length)
                length = int.from_bytes(self.buffer[1:3], byteorder="little")
        else: 
            # must be an L1/L2 context block so read in enough data to have two 
            # bytes in the buffer
            self.__readToBuffer(2 - self.__total_length)
            length = int.from_bytes(self.buffer[1:2], byteorder="little")

        # Set length to current 
        self.__block_length = length
        self.state = self.__stateReadContents
        return

    def __stateReadContents(self):

        if self.
        self.__readToBuffer(1)
        pass

    def __stateValidBlock(self):
        pass
    def __statePopBuffer(self):
        pass


def read_file(file : RawIOBase):
    
    # Create parser
    parser = CryodecoderParser(file)
    
    while (not parser.finished()):
        parser.update()

    return parser
