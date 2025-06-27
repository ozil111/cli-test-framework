import re
from typing import Any, Pattern

class Assertions:
    @staticmethod
    def equals(actual: Any, expected: Any, message: str = "") -> bool:
        if actual != expected:
            raise AssertionError(f"{message} Expected: {expected}, but got: {actual}")
        return True

    @staticmethod
    def contains(container: str, item: str, message: str = "") -> bool:
        """
        Check if the item is contained within the container string.
        This method returns True if the item is found anywhere within the container,
        even if the container contains other information.
        """
        if item not in container:
            raise AssertionError(f"{message} Expected to contain: {item}")
        return True

    @staticmethod
    def matches(text: str, pattern: str, message: str = "") -> bool:
        if not re.search(pattern, text):
            raise AssertionError(f"{message} Text does not match pattern: {pattern}")
        return True

    @staticmethod
    def return_code_equals(actual: int, expected: int, message: str = "") -> bool:
        if actual != expected:
            raise AssertionError(f"{message} Expected return code: {expected}, got: {actual}")
        return True