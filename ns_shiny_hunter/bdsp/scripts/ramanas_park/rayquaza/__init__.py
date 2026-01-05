import pathlib
from typing import Final

FILEPATH: Final = pathlib.Path(__file__)
DIR: Final = FILEPATH.parent

BASELINE_JSON: Final = DIR / 'baseline.json'

def load_baseline() -> list[float]:
    import json
    with BASELINE_JSON.open() as f:
        return json.load(f)