package main

// Add and Order are the tiny real implementation exercised by the registered steps.
// The harness does not replace the Godog runner with a simulated verdict.
func Add(a, b int) int { return a + b }

type Order struct {
	Cancelled bool
	Charges   int
}

func (o *Order) Cancel() { o.Cancelled = true }

func (o *Order) ReprocessChargeEvent() {
	if !o.Cancelled {
		o.Charges++
	}
}
