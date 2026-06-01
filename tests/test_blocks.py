import pytest

# Import module
import cryodecoder
import cryodecoder.blocks
import cryodecoder.exceptions

@pytest.mark.parametrize("superclass", [
    cryodecoder.blocks.L1DataBlock,
    cryodecoder.blocks.L2OriginBlock,
    cryodecoder.blocks.L3ContextBlock,
])
def test_register_valid_block(superclass):

    # Define a test identifier
    test_identifier = b'\0'

    # Define a test class object
    class test_class(superclass):
        pass

    # Try to register the class
    print(len(cryodecoder.identifier_register[superclass]))
    cryodecoder.register_identifier(test_identifier, test_class)

    # Then attempt to register it again and check we get an exception
    with pytest.raises(cryodecoder.exceptions.IdentifierAlreadyRegisteredError):
        cryodecoder.register_identifier(test_identifier, test_class)

    # Cleanup and delete the registered object
    del cryodecoder.identifier_register[superclass][test_identifier]