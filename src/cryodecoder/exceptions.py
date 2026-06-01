class CryodecoderException(Exception):
    pass

class IdentifierAlreadyRegisteredError(CryodecoderException):
    """
    Raised when attempting to register a block to an identifier that already exists.
    """
    pass

class InvalidIdentifierError(CryodecoderException):
    pass

class InvalidBlockHeader(CryodecoderException):
    pass

class BlockIdentifierMismatch(CryodecoderException):
    pass

class InvalidBlockLevel(CryodecoderException):
    pass