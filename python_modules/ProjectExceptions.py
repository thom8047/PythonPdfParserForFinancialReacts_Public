class ParseError(Exception):
    """
    Base excepton for the entire project

    :Author Edward Thomas
    :param - General exception
    """


class UnknownParsedValue(ParseError):
    """
    Unknown value caught while parsing. Meant to throw an error for me to diagnose.

    :param - Message to pass when raising error.
    :param [] - can pass any number of defined parameters if exception correctly handles them. Example below:

    Can include more than the general message parameter

    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.foo = kwargs.get('foo')"""


class NonConformedTransactionObject(ParseError):
    """
    Transaction Object does not fit what we expect it to. If Transaction has more props than we expect this error is thrown.

    @ParseError: Message to pass when raising error.
    """
