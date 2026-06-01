from typing import Union
from enum import Enum

import cryodecoder
import cryodecoder.blocks
import cryodecoder.exceptions

class Parser:

    # States are READ_IDENTIFIER
    #            READ_LENGTH
    #             

    def __init__(self):

        # Empty buffer to store input data
        self.buffer = b''
        self.buffer_offset = 0
        self.state  = Parser.state_readIdentifier
        self.current_class = None
        self.blocks = []

    def push(self, data : Union[bytes, bytearray]):
        self.buffer += data

    def pop(self, length=1):
        if len(self.buffer) > length - 1:
            print(f"Popping {length}")
            popc = self.buffer[0:length]
            self.buffer = self.buffer[length:]
            self.buffer_offset = 0
            return popc
        
    def __len__(self):
        return len(self.buffer)
    
    def update(self):
        self.state(self)

    def state_readIdentifier(self):

        try:
            
            print(f"Reading identifier: {self.buffer[self.buffer_offset:self.buffer_offset+1]}")
            # If the identifier isn't valid, this will fail
            self.current_class = cryodecoder.blocks.get_block_class_from_identifier(self.buffer[self.buffer_offset])

            print(f"Got class {self.current_class}")
            self.current_level = cryodecoder.blocks.get_block_level_from_class(self.current_class)
            
            self.state = Parser.state_readLength

        except cryodecoder.exceptions.InvalidIdentifierError:
            print(f"Invalid identifier: {self.buffer[self.buffer_offset]}")
            self.pop()

    def state_readLength(self):
        
        # Determine header type
        if self.current_level == 3:
            header_class = cryodecoder.blocks.BlockHeaderL3
        else:
            header_class = cryodecoder.blocks.BlockHeaderL1L2

        print(f"Reading length: {self.buffer}")

        # have we got enough parts of the header in the buffer
        if len(self) >= header_class.byte_width:
            # try and create the header
            self.current_header = header_class(raw=self.buffer[self.buffer_offset:self.buffer_offset+header_class.byte_width])
            # Move on to reading block fields (resetting relevant variables)
            self.current_field_bytes = self.current_class._field_length 
            print(f"Reading {self.current_class} with {self.current_field_bytes} of field")
            self.state = Parser.state_readBlockFields

    def state_readBlockFields(self):
        
        # Bit of an ugly hack here to use the current class to refer to itself
        block_length = self.current_class.block_length(self.current_class)
        if len(self) - self.buffer_offset >= block_length:
            fields = self.buffer[self.buffer_offset+self.current_header.byte_width:self.buffer_offset+block_length]
            # try:
            block = self.current_class(self.current_header, raw_fields=fields)
            self.blocks.append(block)
            self.buffer_offset += block_length
            # except Exception as e:
            #     self.pop()
            self.state = Parser.state_readIdentifier
        else:
            pass 


def read_file(file):

    # Create parser instance
    parser = Parser()

    byte = file.read(1)
    # Read while there are bytes to be read in, or we've not finished 
    # popping elements from the buffer
    while ((byte != None and len(byte) != 0) or len(parser)):

        parser.push(byte)
        parser.update()
        byte = file.read(1)
    
    return parser

# import cryodecoder
# import cryodecoder.blocks
# import cryodecoder.exceptions

# from io import RawIOBase
# from enum import Enum

# class CryodecoderParser:
    
#     def __init__(self, source : RawIOBase, stream_mode=False):
#         """
#         source : the origin of data input (file, serial output, etc.)
#         stream : if true, expect continuous input and continue from EOF
#                  if false, terminate at EOF
#         """
        
#         self.source = source
#         self.stream_mode = False
#         self.__finished = False
#         self.buffer = b''
#         # Assign a default state 
#         self.state = CryodecoderParser.__stateBegin
#         # Assign varaible for storing valid blocks
#         self.blocks = []
#         # Define variable indicating 

#     def update(self):
#         # Call the current state
#         self.state(self)

#     def finished(self):
#         return self.__finished

#     def __readToBuffer(self, size=1):
#         bytes_in = self.source.read(size)
#         if bytes_in != None:
#             self.buffer += bytes_in
#             return bytes_in
#         else:
#             if not self.stream_mode:
#                 self.complete = True
#             return 0

#     def __stateBegin(self):
#         self.__block_identifier = ''
#         self.__block_length = 0
#         self.__total_length = 0

#         # Define a stack object which keeps track of which level we are at
#         self.__stack = []
#         self.__stack_level = None

#     def __stateReadBlockIdentifier(self):
        
#         # Read in a new byte
#         self.__readToBuffer()
#         # Get current block identifier
#         temp_block_identifier = self.buffer[0]

#         # Check it is valid
#         block_class = cryodecoder.blocks.get_block_class_from_identifier(temp_block_identifier)
#         if (block_class == None):
#             # Not a valid or registered identifier
#             self.state = self.__statePopBuffer
#             return
        
#         level = cryodecoder.blocks.get_block_level_from_class(block_class)
#         # If we have items in the stack, check that the new identifier is less
#         # than the block level at the end of the state
#         if len(self.__stack) > 0 and \
#             level >= cryodecoder.blocks.get_block_level_from_class(self.__stack[-1].__class__):
#             # We've failed that condition so raise an invalid packet error
#             raise cryodecoder.exceptions.InvalidBlockLevel()

#         # Assign temporary class
#         self.__current_block_class = block_class
        
#         # Move onto next step - read the length
#         self.state = self.__stateReadBlockLength
#         return

#     def __stateReadBlockLength(self):
        
#         # Check what our current class type is L3
#         length = 0
#         if self.__current_block_class == cryodecoder.blocks.L3ContextBlock:
#             if (self.__total_length < 3):
#                  # if so, read in enough data that we have 3 bytes in the buffer
#                 self.__readToBuffer(3 - self.__total_length)
#                 length = int.from_bytes(self.buffer[1:3], byteorder="little")
#         else: 
#             # must be an L1/L2 context block so read in enough data to have two 
#             # bytes in the buffer
#             self.__readToBuffer(2 - self.__total_length)
#             length = int.from_bytes(self.buffer[1:2], byteorder="little")

#         # Set length to current 
#         self.__block_length = length
#         self.state = self.__stateReadContents
#         return

#     def __stateReadContents(self):

#         if self.
#         self.__readToBuffer(1)
#         pass

#     def __stateValidBlock(self):
#         pass
#     def __statePopBuffer(self):
#         pass


# def read_file(file : RawIOBase):
    
#     # Create parser
#     parser = CryodecoderParser(file)
    
#     while (not parser.finished()):
#         parser.update()

#     return parser
