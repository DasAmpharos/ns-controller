from enum import StrEnum, auto


class State(StrEnum):
    ENTRANCE_1 = auto()
    ENTRANCE_2 = auto()
    ENTRANCE_CONFIRMATION = auto()
    FOLLOW_ME = auto()
    BATTLE = auto()
    TARGETED = auto()
    OUTCOME_FAILURE = auto()
    OUTCOME_SUCCESS = auto()
    CANNOT_AFFORD = auto()
    FLY_TO_POKEMON_CENTER = auto()
    POKEMON_CENTER_DIALOG = auto()
    FLY_TO_SUSHI_HIGH_ROLLER = auto()
