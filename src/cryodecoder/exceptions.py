class CryodecoderException(Exception):
    pass

class InvalidNestedBlockError(CryodecoderException):
    """raised when a block has been detected or is being appended within an
    invalid context (i.e. a L3 block nested within an L2 block). We enforce
    that only blocks with levels smaller than the current block are valid to
    be nested (i.e. L3 can nest L2 and L1, L2 can nest L1)
    """
    pass

class PayloadAccessError(CryodecoderException):
    """raised when an attempt is made to set the value or raw value of a Payload
    field
    """
    pass

class InvalidPacketError(CryodecoderException):
    """raised when packet being read in by a parser is invalid
    """