class UserNotFound(Exception):
    def __init__(self, message: str = ''):
        Exception.__init__(self, message)
        self.message = message


class CurrencyNotFound(Exception):
    def __init__(self, message: str = ''):
        Exception.__init__(self, message)
        self.message = message
