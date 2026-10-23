package specmdgodog

import (
	"bytes"
	"encoding/json"
	"fmt"
	"strings"
	"testing"

	"github.com/cucumber/godog"
)

func fixture(expected int) Input {
	return Input{Schema: 1, Features: []FeatureInput{{Path: "docs/soma.md", Block: 2, Line: 10,
		Content: fmt.Sprintf("# language: pt\nFuncionalidade: Soma\n  @SMD-SCN-001\n  Cenário: Somar\n    Dado os números 2 e 3\n    Quando a soma for calculada\n    Então o resultado deve ser %d\n", expected)}},
		ExpectedScenarios: []ExpectedScenario{{ID: "SMD-SCN-001", Path: "docs/soma.md", Block: 2, Line: 13}}}
}

func sumSteps(sc *godog.ScenarioContext) {
	var a, b, result int
	sc.Step(`^os números (\d+) e (\d+)$`, func(x, y int) { a, b = x, y })
	sc.Step(`^a soma for calculada$`, func() { result = a + b })
	sc.Step(`^o resultado deve ser (\d+)$`, func(expected int) error {
		if result != expected {
			return fmt.Errorf("sum=%d, expected=%d", result, expected)
		}
		return nil
	})
}

func TestRealExecutionAndOrigin(t *testing.T) {
	report := Run(fixture(5), sumSteps)
	if !report.Passed || report.EngineFailed || report.DryRun || report.Mode != "real" {
		t.Fatalf("unexpected report: %+v", report)
	}
	if len(report.Scenarios) != 1 || report.Scenarios[0].StepsExecuted != 3 || report.Scenarios[0].Line != 13 || report.Scenarios[0].Block != 2 {
		t.Fatalf("missing real step/source evidence: %+v", report)
	}
}

func TestAssertionFailureAndUndefinedAreNotSuccess(t *testing.T) {
	failed := Run(fixture(6), sumSteps)
	if failed.Passed || !failed.EngineFailed || failed.Scenarios[0].Status != "failed" {
		t.Fatalf("assertion was credited: %+v", failed)
	}
	input := fixture(5)
	input.Features[0].Content = strings.Replace(input.Features[0].Content, "a soma for calculada", "um passo não implementado", 1)
	undefined := Run(input, sumSteps)
	if undefined.Passed || !undefined.EngineFailed || undefined.Scenarios[0].Status != "undefined" {
		t.Fatalf("undefined step was credited: %+v", undefined)
	}
}

func TestMissingExtraOriginAndZeroFailClosed(t *testing.T) {
	for _, mutate := range []func(*Input){
		func(i *Input) { i.ExpectedScenarios = nil },
		func(i *Input) { i.ExpectedScenarios[0].ID = "" },
		func(i *Input) { i.ExpectedScenarios[0].Line++ },
		func(i *Input) { i.Features = nil },
	} {
		input := fixture(5)
		mutate(&input)
		report := Run(input, sumSteps)
		if report.Passed || len(report.Errors) == 0 {
			t.Fatalf("invalid input was credited: %+v", report)
		}
	}
}

func TestOpaqueIDMatchesScenarioByOrigin(t *testing.T) {
	input := fixture(5)
	input.Features[0].Content = strings.Replace(input.Features[0].Content, "  @SMD-SCN-001\n", "\n", 1)
	input.ExpectedScenarios[0].ID = "docs/soma.md::Somar"
	report := Run(input, sumSteps)
	if !report.Passed || len(report.Scenarios) != 1 || report.Scenarios[0].ID != "docs/soma.md::Somar" {
		t.Fatalf("untagged scenario was not matched by origin: %+v", report)
	}
}

func TestOutlineAndRuleExplicitlyUnsupported(t *testing.T) {
	for _, source := range []string{
		"# language: pt\nFuncionalidade: Soma\n @SMD-SCN-001\n Esquema do Cenário: Somar\n  Dado os números <a> e 3\n Exemplos:\n  | a |\n  | 2 |\n",
		"# language: pt\nFuncionalidade: Soma\n Regra: Uma regra\n  @SMD-SCN-001\n  Cenário: Somar\n   Dado os números 2 e 3\n",
	} {
		input := fixture(5)
		input.Features[0].Content = source
		report := Run(input, sumSteps)
		if report.Passed || len(report.Errors) == 0 || !strings.Contains(report.Errors[0], "unsupported") {
			t.Fatalf("unsupported construct not refused: %+v", report)
		}
	}
}

func TestServeProducesOneJSONReport(t *testing.T) {
	encoded, err := json.Marshal(fixture(5))
	if err != nil {
		t.Fatal(err)
	}
	var output bytes.Buffer
	code := Serve(bytes.NewReader(encoded), &output, func(sc *godog.ScenarioContext) { fmt.Println("step initialization log"); sumSteps(sc) })
	var report Report
	if code != 0 || json.Unmarshal(output.Bytes(), &report) != nil || !report.Passed {
		t.Fatalf("invalid protocol output: code=%d %s", code, output.String())
	}
}
