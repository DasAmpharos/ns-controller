package spidata

import (
	"embed"
	"fmt"
	"io/fs"
	"strconv"
	"strings"
	"sync"
)

//go:embed data/*.bin
var binFiles embed.FS

var (
	once sync.Once
	rom  map[uint8][]byte
)

func load() map[uint8][]byte {
	m := make(map[uint8][]byte)
	entries, err := fs.ReadDir(binFiles, "data")
	if err != nil {
		panic(fmt.Sprintf("spidata: failed to read embedded data dir: %v", err))
	}
	for _, e := range entries {
		name := strings.TrimSuffix(e.Name(), ".bin")
		addr, err := strconv.ParseUint(name, 0, 8)
		if err != nil {
			continue
		}
		data, err := binFiles.ReadFile("data/" + e.Name())
		if err != nil {
			panic(fmt.Sprintf("spidata: failed to read %s: %v", e.Name(), err))
		}
		m[uint8(addr)] = data
	}
	return m
}

// Get returns the SPI ROM data for the given page address, or nil if unknown.
func Get(addr uint8) []byte {
	once.Do(func() { rom = load() })
	return rom[addr]
}
