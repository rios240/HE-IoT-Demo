# Generic exceptions created in the applications

class GenericError(Exception):
    def __init__(self, message):
        super().__init__(message)

