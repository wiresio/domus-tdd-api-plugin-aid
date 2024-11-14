from tdd.errors import AppException


class AMLDecodeError(AppException):
    def __init__(self, error):
        super().__init__(
            f"The AML input did not pass the XML Decoding: {str(error)}",
            f"L'entrée AML n'a pas passé le décodage XML: {str(error)}",
            f"Die AML Eingabe hat die XML-Decodierung nicht bestanden: {str(error)}",
        )
