from enum import StrEnum, auto


class State(StrEnum):
    OPEN_MAP = auto()
    TRAVEL_HERE = auto()
    OVERWORLD = auto()
