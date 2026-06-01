# Module for cryodecoder
import cryodecoder.blocks
from cryodecoder.exceptions import IdentifierAlreadyRegisteredError
from cryodecoder.parser import read_file

# __all__ = [
#     "read_file", "identifier_register"
# ]

# Import modules
import logging
logger = logging.getLogger(__name__)

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
    cryodecoder.blocks.register_identifier(block.identifier, block)

logger.log(logging.DEBUG, "Finished loading cryodecoder!")