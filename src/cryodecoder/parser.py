import argparse 
import logging
import serial

import cryodecoder
import cryodecoder.blocks
import cryodecoder.exceptions

# Define a decorator for the parser stack
def _parserstackfunction(method):
    def stackmethod(self, index=None):
        if index is None:
            return method(self, self._stack)
        else:
            return method(self, index)
    return stackmethod

class Parser:

    def __init__(self):
        # Buffer to store valid blocks in
        self._blocks = []
        # Buffer to store input to
        self._buffer : bytes = b''
        # Stack values
        self.reset_stack_variables()
        # Setup state
        self._state = Parser.state_readIdentifier
            
    def reset_stack_variables(self):
        # Stack values
        self._stack = 0
        self._length_bytes     = 0
        self._init_level       = None
        self._block_length : list[int] = [None,None,None]
        self._bytes_remaining : list[int]  = [None, None, None]
        self._fields_remaining : list[int] = [None, None, None]
        self._block : list[cryodecoder.blocks.Block] = [None,None,None]
        return


    def push(self, raw : bytes):
        """assign raw data to local raw buffer
        """
        self._buffer += raw

    def pop(self, count=1):
        """pop the top off the buffer
        """
        if len(self._buffer) >= count + 1:
            self._buffer = self._buffer[count:]
        else:
            self._buffer = b''

    def complete(self):
        """if we have finished processing the buffer, return true
        """
        return len(self._buffer) == 0 and self._init_level == None # TODO: add some state relevant condition here

    def available(self):
        return len(self._blocks)

    def read(self):
        """return the next available block
        """
        if self.available():
            # Return first block
            return self._blocks.pop(0)
        
    def update(self):
        self._state(self)

    def state_readIdentifier(self):

        # print(f"[rI | fields({self._fields_remaining}), bytes({self._bytes_remaining})]")

        # Invalid block
        if not self._buffer[0:1] in cryodecoder.blocks.blocks:
            # print(f"[rI] Invalid identifier {self._buffer[0:1]}, {self._fields_remaining[self._stack]}, {self._bytes_remaining[self._stack]}")
            
            # We might have come from the end of a block with an extra field
            if self._fields_remaining[self._stack] is not None and \
               self._bytes_remaining[self._stack] is not None and \
               self._fields_remaining[self._stack] > 0 and \
               self._bytes_remaining[self._stack] > 0:
                self._state = Parser.state_readField
                return
            # Otherwise, it's simply and invalid identifier
            else:
                self.pop()
                return
        
        # Get block type
        block_type = cryodecoder.blocks.blocks[self._buffer[0:1]]
        # print(f"[rI] Valid identifier {self._buffer[0:1]}")
        
        # If we haven't initialised then 
        if self._init_level is None:
            self._init_level = block_type.level.value
            # Assign block stack based on level
            self._stack = block_type.level.value - 1

        # Check whether the block is less than or equal to the current level
        if block_type.level.value - 1 <= self._stack:
            self._stack = block_type.level.value - 1
        else:
            # print(f"Invalid level {block_type.level.value} (stack={self._stack + 1})")
            self.pop()
            return
        
        # print(f"Setting stack to {self._stack}")

        # Assign block type
        self._block[self._stack] = block_type()

        # get rid of top of the buffer, we've stored the block type
        self.pop()
        # and decrease the byte count for every block above this
        for level in range(self._stack + 1, self._init_level):
            self._bytes_remaining[level] -= 1

        # Move to next state
        self._state = Parser.state_readLength
        return

    def state_readLength(self):

        # print(f"[rL | fields({self._fields_remaining}), bytes({self._bytes_remaining})]")

        length_bytes = self._block[self._stack].header.length_byte_width
        # Check if we don't have enough bytes to read in a full block
        if len(self._buffer) < length_bytes:
            # keep waiting
            return 
        
        # Get length
        length = self._buffer[0:length_bytes]
        
        # print(f"Reading {length_bytes} bytes as length={length}")
        # Assign bytes remaining
        self._bytes_remaining[self._stack] = int.from_bytes(length, "little")
        self._block_length[self._stack] = int.from_bytes(length, "little")
        # Assign fields remaining
        self._fields_remaining[self._stack] = len(self._block[self._stack].fields)

        # If we have bytes or fields remaining then read a field, otherwise
        # we go straight to appending a block
        if self._bytes_remaining[self._stack] or self._fields_remaining[self._stack]:
            # Drop the length, we've stored this
            self.pop(length_bytes)
            # and decrease the byte count for every block above this
            for level in range(self._stack + 1, self._init_level):
                self._bytes_remaining[level] -= length_bytes
            # move to readField
            self._state = Parser.state_readField
            return
        else:
            # otherwise, try and append this block
            self._state = Parser.state_appendBlock
            self.update()
            return

        return

    def state_readField(self):

        # print(f"[rF | fields({self._fields_remaining}), bytes({self._bytes_remaining})]")
        
        # Calculate index of the field we're dealing with
        field_index = len(self._block[self._stack].fields) - self._fields_remaining[self._stack]
        # Store field
        field = getattr(self._block[self._stack], self._block[self._stack].fields[field_index].field_name)

        # Check if we have a payload byte
        if isinstance(field, cryodecoder.blocks.Payload):
            # Decrease field count
            self._fields_remaining[self._stack] -= 1
            # Go to readIdentifier
            self._state = Parser.state_readIdentifier
            return

        # Otherwise, we need to read the field in
        if len(self._buffer) < field.byte_width:
            # stay in this state
            return
        else:
            # print(f"Assinging {field.field_name} as {self._buffer[0:field.byte_width]}")
            # We have enough bytes
            field.raw = self._buffer[0:field.byte_width]
            # Decrease the field count
            self._fields_remaining[self._stack] -= 1
            # Decrease bytes for every block including this
            for level in range(self._stack, self._init_level):
                self._bytes_remaining[level] -= field.byte_width
            self.pop(field.byte_width)

        # Now we have determined the field, we need to check whether we are
        # in an MBus block with a CI_FIELD = 0xAA as this will indicate that
        # the packet format is the original one rather than 
        if isinstance(self._block[self._stack], cryodecoder.blocks.Block_M_MBusPacket) and field.field_name == "ci_field" and field.raw == b'\xAA': # Legacy packet
            pass # debug legacy field
            for legacy_class in (
                cryodecoder.blocks.Block_M_MBusPacketCryoegg2023,
                cryodecoder.blocks.Block_M_MBusPacketCryowurst2023,
            ):
                # Create test object
                test_block = legacy_class()
                # Get expected block length of that object
                if self._block_length[self._stack] == \
                    test_block.header.calculate_block_length(test_block):
                    # Increment remaining fields by the difference between
                    # this and the old block
                    self._fields_remaining[self._stack] += \
                    len(test_block.fields) - len(self._block[self._stack].fields)
                    # Convert to new block
                    for field in self._block[self._stack].fields:
                        # Assign existing fields
                        if hasattr(test_block, field.field_name):
                            getattr(test_block, field.field_name).raw = field.raw
                    # Don't need to complete this step for another packet type
                    self._block[self._stack] = test_block
                    break

        # Check whether we have any bytes left
        if self._fields_remaining[self._stack] <= 0:
            if self._bytes_remaining[self._stack] <= 0:
                # Move to append this block
                self._state = Parser.state_appendBlock
                self.update()
                return
            else:
                self._state = Parser.state_readIdentifier 
                return
        else:
            # We still have fields to read
            self._state = Parser.state_readField
            return
            
    def state_appendBlock(self):

        # print(f"[aB | fields({self._fields_remaining}), bytes({self._bytes_remaining})]")
            
        # Save the block
        block = self._block[self._stack]
        # Make the current block empty
        self._block[self._stack] = None

        # Check we are not at the top of the stack
        if self._stack < self._init_level - 1:

            # Increment the stack
            self._stack += 1
            # implicit guarantee that L2 and L3 blocks are of type BlockChildren - TODO: worth checking?
            self._block[self._stack].add_child(block)
            # print(f"Assigned {block} to {self._block[self._stack]}")

            # fields == 0 -> no more fields, bytes == 0 -> no more blocks
            if self._fields_remaining[self._stack] == 0 and \
                self._bytes_remaining[self._stack] == 0:
                # then we can append the next block too)
                self._state = Parser.state_appendBlock
                self.update()
                return
            elif self._fields_remaining[self._stack] >= 0 and \
                self._bytes_remaining[self._stack] > 0:
                # We're done processing this block but are expecting
                # another one at the same level
                self._state = Parser.state_readIdentifier
                return
            # elif self._fields_remaining[self._stack] > 0 and :
            #     self._state = Parser.state_readField

        # We are at the top level
        else:

            # Append block to top level
            self._blocks.append(block)
            # print(f"Assigned {block} to parser stack")
            # print(f"[{len(self._buffer)}] {self._buffer}")

            # Reset variables
            self.reset_stack_variables()
            self._state = Parser.state_readIdentifier
            return

        return
    
class SerialDecoder:

    def __init__(self, port="COM1", baud_rate=19200):

        self.port = port
        self.baud_rate = baud_rate

        self._serial = serial.Serial(port, baud_rate)
        self._parser = Parser()

        self._file = ""

    def run(self):

        print("Running decoder...")
        # self._serial.open()

        while True:
            try:
                byte = self._serial.read(1)
                while ((byte != b'') or not self._parser.complete()):
                    if (byte == b'#'):
                        # Read until end of line
                        print("Decoder log:", end="")
                        byte = self._serial.read(1)
                        while (byte != b'\n' and byte != b'\r'):
                            print(byte.decode("ascii"), end="")
                            byte = self._serial.read(1)
                        byte = self._serial.read(1)
                        print(byte)
                    else:
                        # print(f"{byte.hex()} -> {byte.decode("ascii") if byte[0] < 128 and byte[0] > 32 else f"({byte[0]})"}")
                        self._parser.push(byte)
                        self._parser.update()

                    if self._parser.available():
                        break

                    byte = self._serial.read(1)

                if self._parser.available():
                    print("BLOCK AVAILABLE!")
                    self.__processBlocks()

            except KeyboardInterrupt:
                self._serial.close()
                self.save()
                return
        
    def save(self):
        pass

    def __processBlocks(self):

        # We've accidentally ended up here
        if not self._parser.available():
            return
        
        while self._parser.available():
            block = self._parser.read()
            print(block)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        prog='parser.py',
        description='Runs a file-based or Serial decoder for Cryoegg packets.',
        epilog='See [URL] for more help.'
    )
    
    parser.add_argument("type", choices=["serial", "file"]
                        )
    parser.add_argument("-p", "--port", type=str, required=False, default="COM1")
    parser.add_argument("-b", "--baud", type=int, required=False, default=19200)

    args = parser.parse_args()

    if args.type == "serial":

        print(f"Starting serial decoder with port {args.port}")
        try:
            serialDecoder = SerialDecoder(port=args.port, baud_rate=args.baud)
            serialDecoder.run()
        except KeyboardInterrupt:
            serialDecoder.save()
            print("Quitting...")
            exit()

    else:

        print("No type provided, shutting down.")