# Module for cryodecoder
import cryodecoder.blocks
from cryodecoder.exceptions import IdentifierAlreadyRegisteredError
from cryodecoder.parser import read_file

__all__ = [
    "read_file", "identifier_register"
]

# Import modules
import logging
cryodecoder_logger = logging.getLogger(__name__)

# Keep a register of the blocks and their respective identifiers
# which allows for registration of new identifiers 'on-the-fly' 
identifier_register = {
    cryodecoder.blocks.L1DataBlock : {
    },
    cryodecoder.blocks.L2OriginBlock : {        
    },
    cryodecoder.blocks.L3ContextBlock :{
    }
}

# Now we've created the register record, assign the existing/default
# blocks to it. To do this, we expose the register_identifier method
def register_identifier(identifier, block_class):

    # Validate identifier
    identifier = cryodecoder.blocks.sanitise_identifier(identifier)

    if issubclass(block_class, cryodecoder.blocks.L3ContextBlock) and \
        identifier in (b'W', b'C'):
        # Treat 'W' and 'C' as reserved identifiers
        raise IdentifierAlreadyRegisteredError(identifier)

    # Iterate over each class type
    for class_type in identifier_register:
        # If we are an instance of this class, then see if the identifier is 
        # already registered and if not - register it!
        if issubclass(block_class, class_type): 
            if not identifier in identifier_register[class_type]:
                identifier_register[class_type][identifier] = block_class
                cryodecoder_logger.log(logging.DEBUG, f"Registered block identifier {identifier} to {block_class}")
                return
            else:
                # otherwise, raise an error to deal with it
                raise IdentifierAlreadyRegisteredError(identifier)
    
    # If we reach this point, we've exhausted the class_types
    raise ValueError(f"Class {block_class} should be a subclass of one of L1DataBlock, L2OriginBlock or L3ContextBlock")

# Register the default blocks
## L1 
for block in (
    cryodecoder.blocks.LSM303AGRBlock,
    cryodecoder.blocks.BMA400Block,
    cryodecoder.blocks.CryoBlock,
    cryodecoder.blocks.EnvironmentalBlock,
    cryodecoder.blocks.KellerPressureBlock,
    cryodecoder.blocks.CTiTiltBlock,
    cryodecoder.blocks.PowerStatusBlock,
    cryodecoder.blocks.MBusOriginBlock,
    cryodecoder.blocks.ReceiverOriginBlock,
    cryodecoder.blocks.DataContextBlock,
    cryodecoder.blocks.HousekeepingContextBlock
):
    register_identifier(block.identifier, block)

cryodecoder_logger.log(logging.DEBUG, "Finished loading cryodecoder!")