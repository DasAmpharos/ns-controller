import threading
from typing import TypeVar, Generic, Optional

T = TypeVar('T')


class AtomicValue(Generic[T]):
    def __init__(self, value: Optional[T] = None):
        self.__lock = threading.Lock()
        self.__value = value

    def compare_and_set(self, expected: T, value: T) -> bool:
        with self.__lock:
            if self.__value == expected:
                self.__value = value
                return True
            return False

    def get(self) -> T:
        try:
            with self.__lock:
                return self.__value
        except KeyboardInterrupt:
            pass

    def set(self, value: T):
        try:
            with self.__lock:
                self.__value = value
        except KeyboardInterrupt:
            pass