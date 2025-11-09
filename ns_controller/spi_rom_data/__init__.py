import functools
import pathlib
from types import MappingProxyType

ReadonlyDict = MappingProxyType


@functools.cache
def load() -> ReadonlyDict[int, bytes]:
    filepath = pathlib.Path(__file__)
    return ReadonlyDict({
        int(bin_file.stem, 16): bin_file.read_bytes()
        for bin_file in filepath.parent.glob("*.bin")
    })

def get(addr: int) -> bytes | None:
    spi_rom_data = load()
    return spi_rom_data.get(addr, None)