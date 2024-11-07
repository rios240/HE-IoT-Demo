from http import HTTPStatus


# Generic exceptions created in the applications
class GenericError(Exception):
    def __init__(self, message):
        super().__init__(message)


# Exception class used by Flask to return errors
class InvalidUsage(Exception):
    status = HTTPStatus.BAD_REQUEST     # 400

    def __init__(self, message="Unknown error", status=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status is not None:
            self.status = status
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv["ok"] = False
        rv["error"] = self.message
        return rv
