Parser logic
============
This scetion of the documentation describes the logic of the :py:class:`cryodecoder.parser.Parser` object. The parser is designed for the latest version of CHIL instrument protocol, and to be backwards compatible with previous packet formats.

The parser has an internal first-in first-out (FIFO) buffer which accepts bytes to parse as CHIL blocks. Bytes are assigned to the parser with the :py:classmethod:`push <cryodecoder.parser.Parser.push>` method. 

State machine
-------------
The parsing logic is implemented in a state machine which consists of four primary states: *readIdentifier*, *readLength*, *readField* and *appendBlock*. Here, the states are listed in the logical order of occurence: 

1. **readIdentifier**: The parser checks for a valid block identifier.
2. **readLength**: It then reads the length of the number of bytes to follow. If these are both valid, then a new instance of the block is created.
3. **readField**: Each field within the block is read and stored in the block instance..
4. **appendBlock**: The finished block is stored in a buffer.

When a block is finished, the state machine returns to *readIdentifier*, which starts the process of reading the next block.

.. important::

    The current implementation of the parser does not automatically update the state machine after a byte has been added.

    To progress the parser and update the state machine, the user should call the :py:classmethod:`update <cryodecoder.parser.Parser.update>` method for each byte in the buffer.

State: readIdentifier
^^^^^^^^^^^^^^^^^^^^^
This section describes the steps involved in the *readIdentifier* state.

1.  
    The parser checks whether the current block is identifier is valid by comparing against the identifiers stored in :py:data:`cryodecoder.blocks.blocks`.
2.
    If the identifier is not valid, it is possible that we may have returned to *readIdentifier* from a lower level block and we still have fields remaining at the current level. We keep track of how many fields we expect at the current level, so if we do not not have any bytes remaining or we don't expect to read another field
3.
    If the **identifier is valid**, then we find the class associated with the ASCII identifier (i.e. ``A``, ``M``, etc.).

    .. note::

        Older versions of the Cryoegg packets begin with a ``C``, which is the same as :ref:`CHIL blocks <block_c_chil>`. The difference between these is the length, which is handled in the **readLength** step.
4.
    Before continuing, we also check that the current block is valid based on its level as we do not permit higher level blocks to be nested within lower ones.
5. 
    Now that we are sure the identifier is valid, we initialise the stack variables at the level of the current block and continue to **readLength**.

State: readLength
^^^^^^^^^^^^^^^^^
This state generally follows **readIdentifier** state and checks the length of the upcoming block. This allows the parser to handle cases where the same block identifier (i.e. ``C``) can be associated with different content based on its length.

1.  
    If there are fewer bytes in the current buffer than the length byte, the parser stays in the same state to keep waiting until we have received that many bytes.

2.  
    The parser checks if the current block identifier is ``C`` or ``W``. If so, the parser checks whether the identifier and length bytes together are:

    *   ``C1``: packet from the second iteration of the Cryoegg receiver (:py:class:`Block_C_Cryoegg <cryodecoder.blocks.Block_C_Cryoegg>`).
    *   ``W1``: packet from the first iteration of the Cryowurst receiver (:py:class:`Block_W1_Wurst <cryodecoder.blocks.Block_W1_Wurst>`).
    *   ``W2``: packet from the second iteration of the Cryowurst receiver (:py:class:`Block_W_Wurst <cryodecoder.blocks.Block_W_Wurst>`).

3.  
    For newer block types, the current byte is used as the block length. If a legacy block type has been detected (see previous step), the parser determines the expected block length using the block definition.

4.
    Finally, the parser checks whether the current block has fields or bytes remaining. If so, the next state is **readField**. Otherwise, the parser moves to **appendBlock**.

State: readField
^^^^^^^^^^^^^^^^
In this state, the parser waits for the correct number of bytes and then populates the relevant field within the current block.

1.  
    The first step is to determine which field is being used. This is achieved by converting the number of fields remaining to an offset which maps to the ``field_order`` property of the :py:class:`Field <cryodecoder.blocks.Field>` class.

2.
    Before processing the current byte, the parser checks whether it is dealing with a :py:class:`Payload <cryodecoder.blocks.Payload>` field. This is a special type of field which allows for blocks to be embedded *within* the current block - such as the :py:class:`Block_M_MBusPacket <cryodecoder.blocks.Block_M_MBusPacket>` block. If so, we decrease the number of fields by 1 and return to **readIdentifer**.

3.
    With the correct number of bytes available, the raw value of the field is assigned to the bytes in the buffer and the number of fields at the current level is decreased by one. To ensure the stack remains value, the number of bytes remaining is decreased for each level above the current one. Finally, the bytes are removed from the buffer.

4. 
    To process a field, the parser needs the correct number of bytes available (determined by the ``byte_width`` parameter in :py:class:`Field <cryodecoder.blocks.Field>`). The parser remains in the current state until the correct number of bytes are available.

5.  
    To handle the case where a legacy (2023) instrument is received by a newer datalogger, if the current block is :py:class:`Block_M_MBusPacket <cryodecoder.blocks.Block_M_MBusPacket>` the parser checks whether the ``ci_field`` parameter is equal to ``AA`` or ``AC``.

    The parser then checks against :py:class:`Block_M_MBusPacketCryoegg2023 <cryodecoder.blocks.Block_M_MBusPacketCryoegg2023>` and :py:class:`Block_M_MBusPacketCryowurst2023 <cryodecoder.blocks.Block_M_MBusPacketCryowurst2023>` to see which type the parser is dealing with based on the number of fields remaining (which are unique for these types).

6.
    If there are no more fields remaining, then the parser checks whether there are bytes remaining:

    a.  If the are no bytes remaining, change state to **appendBlock**.
    b.  If there are bytes remaining, revert to **readIdentifier**.

    Otherwise, there are still more fields to be read at the current level so the state remains as **readField**.

State: appendBlock
^^^^^^^^^^^^^^^^^^
In this state, the parser assumes that it has a complete block and is ready to make it available to the user.

1.  
    Before anything else, the parser saves a copy of the block in the current level of the stack.

2.
    Then, the parser checks that the current level (stored in ``_stack``) is less than the level at which the parser was initialised. 

    a.  
        If the parser is not at the top level of the stack, then the current block is added to the block above as a *child block*. If there are no more fields remaining and no more bytes remaining, the next block is appended by calling ``update()``. If there are bytes remaining, then we expect another one at the same level so change state to **readIdentifier**.

    b.
        If the parser is at the top level of the stack, then the current block is added to the parser's buffer with the current timestamp. The stack variables are then reset and the state is changed to **readIdentifier**.

Stack variables
---------------
The :py:class:`Parser <cryodecoder.parser.Parser>` object maintains a stack which keeps track of parameters for the different block levels within the data protocol. The ``_stack`` variable stores the current block level and is used to index the remaining stack parameters:

* ``_block_length``: stores the expected length of the current block.
* ``_bytes_remaining``: stores the number of bytes remaining at the current layer of the stack.
* ``_fields_remaining``: stores the number of fields remaining at the current layer of the stack. 
* ``_block``: stores the :py:class:`Block <cryodecoder.blocks.Block>` subclass associated with the current block.