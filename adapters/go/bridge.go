// Package specmdgodog runs caller-supplied Markdown Gherkin blocks with Godog.
// It produces execution evidence; it does not grant human contract acceptance.
package specmdgodog

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"io/fs"
	"os"
	"regexp"
	"sort"
	"strings"

	gherkin "github.com/cucumber/gherkin/go/v42"
	"github.com/cucumber/godog"
)

type FeatureInput struct {
	Path    string `json:"path"`
	Block   int    `json:"block"`
	Line    int    `json:"line"`
	Content string `json:"content"`
}

type ExpectedScenario struct {
	ID    string `json:"id"`
	Path  string `json:"path"`
	Block int    `json:"block"`
	Line  int    `json:"line"`
}

type Input struct {
	Schema            int                `json:"schema"`
	Features          []FeatureInput     `json:"features"`
	ExpectedScenarios []ExpectedScenario `json:"expected_scenarios"`
}

type StepResult struct {
	Status string `json:"status"`
	Text   string `json:"text"`
}

type ScenarioResult struct {
	ID            string       `json:"id"`
	Path          string       `json:"path"`
	Block         int          `json:"block"`
	Line          int          `json:"line"`
	Status        string       `json:"status"`
	StepsExecuted int          `json:"steps_executed"`
	Steps         []StepResult `json:"steps"`
}

type Report struct {
	Schema       int              `json:"schema"`
	Mode         string           `json:"mode"`
	DryRun       bool             `json:"dry_run"`
	EngineFailed bool             `json:"engine_failed"`
	Scenarios    []ScenarioResult `json:"scenarios"`
	Passed       bool             `json:"passed"`
	Errors       []string         `json:"errors,omitempty"`
}

var scenarioID = regexp.MustCompile(`^SMD-(?:[A-Za-z0-9]+-)*SCN-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*$`)

type declaration struct {
	ExpectedScenario
	URI   string
	Steps int
}

type noFeatureFS struct{}

func (noFeatureFS) Open(name string) (fs.File, error) {
	return nil, fmt.Errorf("feature filesystem access is disabled: %s", name)
}

func emptyReport() Report {
	return Report{Schema: 1, Mode: "real", EngineFailed: true, Scenarios: []ScenarioResult{}}
}

// prepare validates the parsed declarations, independently of expected IDs.
// Rules and outlines are rejected rather than credited as a template execution.
func prepare(input Input) ([]godog.Feature, map[string]declaration, error) {
	if input.Schema != 1 || len(input.Features) == 0 || len(input.ExpectedScenarios) == 0 {
		return nil, nil, errors.New("schema 1 requires nonempty features and expected_scenarios")
	}
	wanted := map[string]ExpectedScenario{}
	for _, item := range input.ExpectedScenarios {
		if !scenarioID.MatchString(item.ID) || item.Path == "" || item.Block < 1 || item.Line < 1 {
			return nil, nil, fmt.Errorf("invalid expected scenario: %q", item.ID)
		}
		if _, ok := wanted[item.ID]; ok {
			return nil, nil, fmt.Errorf("duplicate expected ID: %s", item.ID)
		}
		wanted[item.ID] = item
	}
	features := []godog.Feature{}
	declared := map[string]declaration{}
	blocks := map[string]bool{}
	next := 0
	for _, block := range input.Features {
		if block.Path == "" || block.Block < 1 || block.Line < 1 || block.Line > 1_000_000 || strings.TrimSpace(block.Content) == "" {
			return nil, nil, errors.New("invalid feature path/block/line/content")
		}
		uri := fmt.Sprintf("%s#block-%d", block.Path, block.Block)
		if blocks[uri] {
			return nil, nil, fmt.Errorf("duplicate block: %s", uri)
		}
		blocks[uri] = true
		padded := strings.Repeat("\n", block.Line-1) + block.Content
		doc, err := gherkin.ParseGherkinDocument(strings.NewReader(padded), func() string { next++; return fmt.Sprint(next) })
		if err != nil {
			return nil, nil, fmt.Errorf("%s: %w", uri, err)
		}
		if doc.Feature == nil {
			return nil, nil, fmt.Errorf("no feature: %s", uri)
		}
		dialect := gherkin.DialectsBuiltin().GetDialect(doc.Feature.Language)
		if dialect == nil {
			return nil, nil, fmt.Errorf("unknown language: %s", doc.Feature.Language)
		}
		for _, tag := range doc.Feature.Tags {
			if scenarioID.MatchString(strings.TrimPrefix(tag.Name, "@")) {
				return nil, nil, errors.New("scenario IDs must be own scenario tags")
			}
		}
		backgroundSteps := 0
		for _, child := range doc.Feature.Children {
			if child.Background != nil {
				backgroundSteps += len(child.Background.Steps)
			}
		}
		for _, child := range doc.Feature.Children {
			if child.Rule != nil {
				return nil, nil, errors.New("unsupported: Rule requires a bridge with rule-aware evidence")
			}
			scenario := child.Scenario
			if scenario == nil {
				continue
			}
			outline := len(scenario.Examples) > 0
			for _, keyword := range dialect.ScenarioOutlineKeywords() {
				if scenario.Keyword == keyword {
					outline = true
				}
			}
			if outline {
				return nil, nil, errors.New("unsupported: Scenario Outline requires concrete instance evidence")
			}
			ids := []string{}
			for _, tag := range scenario.Tags {
				id := strings.TrimPrefix(tag.Name, "@")
				if scenarioID.MatchString(id) {
					ids = append(ids, id)
				}
			}
			if len(ids) != 1 || len(scenario.Steps) == 0 {
				return nil, nil, errors.New("each simple scenario requires one own ID and at least one step")
			}
			id := ids[0]
			if _, ok := declared[id]; ok {
				return nil, nil, fmt.Errorf("duplicate scenario ID: %s", id)
			}
			actual := ExpectedScenario{ID: id, Path: block.Path, Block: block.Block, Line: int(scenario.Location.Line)}
			if expected, ok := wanted[id]; !ok || expected != actual {
				return nil, nil, fmt.Errorf("unknown scenario or origin mismatch: %s", id)
			}
			declared[id] = declaration{ExpectedScenario: actual, URI: uri, Steps: backgroundSteps + len(scenario.Steps)}
		}
		features = append(features, godog.Feature{Name: uri, Contents: []byte(padded)})
	}
	if len(declared) != len(wanted) {
		return nil, nil, errors.New("declared and expected scenario sets differ")
	}
	return features, declared, nil
}

// Run executes actual steps registered by initialize. It never loads .feature
// files, applies tag filters, dry-runs, or grants acceptance of a contract.
func Run(input Input, initialize func(*godog.ScenarioContext)) (report Report) {
	report = emptyReport()
	defer func() {
		if p := recover(); p != nil {
			report.Passed = false
			report.EngineFailed = true
			report.Errors = append(report.Errors, fmt.Sprintf("runner panic: %v", p))
		}
	}()
	features, declared, err := prepare(input)
	if err != nil {
		report.Errors = append(report.Errors, err.Error())
		return
	}
	if initialize == nil {
		report.Errors = append(report.Errors, "ScenarioInitializer is required")
		return
	}
	current := -1
	seen := map[string]int{}
	initializer := func(sc *godog.ScenarioContext) {
		initialize(sc)
		sc.Before(func(ctx context.Context, scenario *godog.Scenario) (context.Context, error) {
			id := ""
			for _, tag := range scenario.Tags {
				candidate := strings.TrimPrefix(tag.Name, "@")
				if scenarioID.MatchString(candidate) {
					if id != "" {
						return ctx, errors.New("multiple runtime IDs")
					}
					id = candidate
				}
			}
			origin, ok := declared[id]
			if !ok || scenario.Uri != origin.URI {
				return ctx, errors.New("unknown runtime scenario or URI")
			}
			seen[id]++
			report.Scenarios = append(report.Scenarios, ScenarioResult{ID: id, Path: origin.Path, Block: origin.Block, Line: origin.Line, Status: "pending", Steps: []StepResult{}})
			current = len(report.Scenarios) - 1
			return ctx, nil
		})
		sc.StepContext().After(func(ctx context.Context, step *godog.Step, status godog.StepResultStatus, stepErr error) (context.Context, error) {
			if current < 0 {
				return ctx, errors.New("step observed without known scenario")
			}
			row := &report.Scenarios[current]
			value := status.String()
			if value == "ambiguous" {
				value = "failed"
			}
			row.Steps = append(row.Steps, StepResult{Status: value, Text: step.Text})
			if value == "passed" || value == "failed" || value == "pending" {
				row.StepsExecuted++
			}
			return ctx, nil
		})
		sc.After(func(ctx context.Context, scenario *godog.Scenario, scenarioErr error) (context.Context, error) {
			if current < 0 {
				return ctx, nil
			}
			row := &report.Scenarios[current]
			row.Status = "passed"
			if errors.Is(scenarioErr, godog.ErrUndefined) {
				row.Status = "undefined"
			} else if errors.Is(scenarioErr, godog.ErrPending) {
				row.Status = "pending"
			} else if scenarioErr != nil {
				row.Status = "failed"
			}
			for _, step := range row.Steps {
				if step.Status != "passed" && row.Status == "passed" {
					row.Status = step.Status
				}
			}
			if (len(row.Steps) != declared[row.ID].Steps || row.StepsExecuted == 0) && row.Status == "passed" {
				row.Status = "failed"
			}
			current = -1
			return ctx, nil
		})
	}
	options := &godog.Options{Format: "progress", NoColors: true, Strict: true, Concurrency: 1, FeatureContents: features, FS: noFeatureFS{}, Output: os.Stderr}
	code := (&godog.TestSuite{Name: "specmd-native", ScenarioInitializer: initializer, Options: options}).Run()
	report.EngineFailed = code != 0
	report.Passed = !report.EngineFailed && len(report.Scenarios) == len(declared) && len(report.Scenarios) > 0
	for _, row := range report.Scenarios {
		if row.Status != "passed" || row.StepsExecuted == 0 || seen[row.ID] != 1 {
			report.Passed = false
		}
		for _, step := range row.Steps {
			if step.Status != "passed" {
				report.Passed = false
			}
		}
	}
	for id := range declared {
		if seen[id] != 1 {
			report.Passed = false
			report.Errors = append(report.Errors, fmt.Sprintf("%s executed %d times; required once", id, seen[id]))
		}
	}
	sort.Slice(report.Scenarios, func(i, j int) bool { return report.Scenarios[i].ID < report.Scenarios[j].ID })
	return
}

// Serve implements the JSON subprocess protocol. Ordinary Go stdout from steps
// is routed to stderr. Arbitrary user code can still bypass this redirection;
// the caller must reject any output that is not exactly one valid report.
func Serve(reader io.Reader, writer io.Writer, initialize func(*godog.ScenarioContext)) int {
	input := Input{}
	decoder := json.NewDecoder(io.LimitReader(reader, 8*1024*1024))
	var report Report
	if err := decoder.Decode(&input); err != nil {
		report = emptyReport()
		report.Errors = []string{err.Error()}
	} else {
		var trailing any
		if decoder.Decode(&trailing) != io.EOF {
			report = emptyReport()
			report.Errors = []string{"expected one JSON input object"}
		} else {
			stdout := os.Stdout
			os.Stdout = os.Stderr
			report = Run(input, initialize)
			os.Stdout = stdout
		}
	}
	if err := json.NewEncoder(writer).Encode(report); err != nil {
		return 2
	}
	if !report.Passed {
		return 1
	}
	return 0
}
