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
            # print(f"[rI] Invalid identifier {self._buffer[0:1]}")
            
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
            print(f"Invalid level {block_type.level.value} (stack={self._stack + 1})")
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

        # Otherwise, we need to read the file in
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
            print(f"Assigned {block} to {self._block[self._stack]}")

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
            print(f"Assigned {block} to parser stack")
            print(f"[{len(self._buffer)}] {self._buffer}")

            # Reset variables
            self.reset_stack_variables()
            self._state = Parser.state_readIdentifier
            return

        return
