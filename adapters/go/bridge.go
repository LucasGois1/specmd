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
	"sort"
	"strings"

	gherkin "github.com/cucumber/gherkin/go/v42"
	"github.com/cucumber/godog"
	messages "github.com/cucumber/messages/go/v34"
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

// originKey identifies a scenario by its place in the Markdown; IDs are opaque.
type originKey struct {
	Path        string
	Block, Line int
}

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

// expectedByOrigin indexes the expected scenarios by origin; IDs are opaque
// but must be unique.
func expectedByOrigin(items []ExpectedScenario) (map[originKey]ExpectedScenario, error) {
	wanted := map[originKey]ExpectedScenario{}
	ids := map[string]bool{}
	for _, item := range items {
		if item.ID == "" || item.Path == "" || item.Block < 1 || item.Line < 1 {
			return nil, fmt.Errorf("invalid expected scenario: %q", item.ID)
		}
		key := originKey{item.Path, item.Block, item.Line}
		if _, ok := wanted[key]; ok || ids[item.ID] {
			return nil, fmt.Errorf("duplicate expected scenario: %s", item.ID)
		}
		wanted[key] = item
		ids[item.ID] = true
	}
	return wanted, nil
}

func isOutline(keyword string, examples int, dialect *gherkin.Dialect) bool {
	if examples > 0 {
		return true
	}
	for _, outline := range dialect.ScenarioOutlineKeywords() {
		if keyword == outline {
			return true
		}
	}
	return false
}

// preparation accumulates declarations while each Markdown block is parsed.
// names maps each block URI and scenario name to IDs in file order.
type preparation struct {
	wanted   map[originKey]ExpectedScenario
	declared map[string]declaration
	names    map[string]map[string][]string
	blocks   map[string]bool
	next     int
}

func (p *preparation) declare(block FeatureInput, uri string, line int, name string, steps int) error {
	expected, ok := p.wanted[originKey{block.Path, block.Block, line}]
	if !ok {
		return fmt.Errorf("unexpected scenario at %s:%d", block.Path, line)
	}
	p.declared[expected.ID] = declaration{ExpectedScenario: expected, URI: uri, Steps: steps}
	p.names[uri][name] = append(p.names[uri][name], expected.ID)
	return nil
}

// addBlock parses one Markdown block. Rules and outlines are rejected rather
// than credited as a template execution.
func (p *preparation) addBlock(block FeatureInput) (godog.Feature, error) {
	if block.Path == "" || block.Block < 1 || block.Line < 1 || block.Line > 1_000_000 || strings.TrimSpace(block.Content) == "" {
		return godog.Feature{}, errors.New("invalid feature path/block/line/content")
	}
	uri := fmt.Sprintf("%s#block-%d", block.Path, block.Block)
	if p.blocks[uri] {
		return godog.Feature{}, fmt.Errorf("duplicate block: %s", uri)
	}
	p.blocks[uri] = true
	padded := strings.Repeat("\n", block.Line-1) + block.Content
	doc, err := gherkin.ParseGherkinDocument(strings.NewReader(padded), func() string { p.next++; return fmt.Sprint(p.next) })
	if err != nil {
		return godog.Feature{}, fmt.Errorf("%s: %w", uri, err)
	}
	if doc.Feature == nil {
		return godog.Feature{}, fmt.Errorf("no feature: %s", uri)
	}
	dialect := gherkin.DialectsBuiltin().GetDialect(doc.Feature.Language)
	if dialect == nil {
		return godog.Feature{}, fmt.Errorf("unknown language: %s", doc.Feature.Language)
	}
	if err := p.declareChildren(block, uri, doc.Feature.Children, dialect); err != nil {
		return godog.Feature{}, err
	}
	return godog.Feature{Name: uri, Contents: []byte(padded)}, nil
}

func (p *preparation) declareChildren(block FeatureInput, uri string, children []*messages.FeatureChild, dialect *gherkin.Dialect) error {
	p.names[uri] = map[string][]string{}
	backgroundSteps := 0
	for _, child := range children {
		if child.Background != nil {
			backgroundSteps += len(child.Background.Steps)
		}
	}
	for _, child := range children {
		if child.Rule != nil {
			return errors.New("unsupported: Rule requires a bridge with rule-aware evidence")
		}
		scenario := child.Scenario
		if scenario == nil {
			continue
		}
		if isOutline(scenario.Keyword, len(scenario.Examples), dialect) {
			return errors.New("unsupported: Scenario Outline requires concrete instance evidence")
		}
		if len(scenario.Steps) == 0 {
			return errors.New("each simple scenario requires at least one step")
		}
		if err := p.declare(block, uri, int(scenario.Location.Line), scenario.Name, backgroundSteps+len(scenario.Steps)); err != nil {
			return err
		}
	}
	return nil
}

// prepare matches parsed scenarios to the expected ones by origin (path,
// block, line).
func prepare(input Input) ([]godog.Feature, map[string]declaration, map[string]map[string][]string, error) {
	if input.Schema != 1 || len(input.Features) == 0 || len(input.ExpectedScenarios) == 0 {
		return nil, nil, nil, errors.New("schema 1 requires nonempty features and expected_scenarios")
	}
	wanted, err := expectedByOrigin(input.ExpectedScenarios)
	if err != nil {
		return nil, nil, nil, err
	}
	p := &preparation{wanted: wanted, declared: map[string]declaration{},
		names: map[string]map[string][]string{}, blocks: map[string]bool{}}
	features := []godog.Feature{}
	for _, block := range input.Features {
		feature, err := p.addBlock(block)
		if err != nil {
			return nil, nil, nil, err
		}
		features = append(features, feature)
	}
	if len(p.declared) != len(wanted) {
		return nil, nil, nil, errors.New("declared and expected scenario sets differ")
	}
	return features, p.declared, p.names, nil
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
	features, declared, names, err := prepare(input)
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
	occurrences := map[string]int{}
	initializer := func(sc *godog.ScenarioContext) {
		initialize(sc)
		sc.Before(func(ctx context.Context, scenario *godog.Scenario) (context.Context, error) {
			// Concurrency is 1, so scenarios run in file order: the nth runtime
			// scenario with a name is the nth declared one in that block.
			key := scenario.Uri + "\x00" + scenario.Name
			candidates := names[scenario.Uri][scenario.Name]
			if occurrences[key] >= len(candidates) {
				return ctx, errors.New("unknown runtime scenario or URI")
			}
			id := candidates[occurrences[key]]
			occurrences[key]++
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
