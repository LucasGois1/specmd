package main

import (
	"fmt"
	"os"

	specmdgodog "example.com/specmd/adapters/go"
	"github.com/cucumber/godog"
)

// Add is real application code used only by this runnable integration example.
func Add(a, b int) int { return a + b }

func initialize(sc *godog.ScenarioContext) {
	var a, b, result int
	sc.Step(`^os números (-?\d+) e (-?\d+)$`, func(x, y int) { a, b = x, y })
	sc.Step(`^a aplicação somar os números$`, func() { result = Add(a, b) })
	sc.Step(`^o resultado deve ser (-?\d+)$`, func(expected int) error {
		if result != expected {
			return fmt.Errorf("Add(%d,%d)=%d; expected %d", a, b, result, expected)
		}
		return nil
	})
}

func main() { os.Exit(specmdgodog.Serve(os.Stdin, os.Stdout, initialize)) }
