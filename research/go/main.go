package main

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"io/fs"
	"os"
	"regexp"
	"runtime"
	"sort"
	"strings"
	"testing/fstest"

	"github.com/cucumber/godog"
	"github.com/yuin/goldmark"
	"github.com/yuin/goldmark/ast"
	"github.com/yuin/goldmark/text"
)

type origin struct {
	Document string `json:"document"`
	Block    int    `json:"block"`
	Line     int    `json:"line"`
}

type observation struct {
	ID     string `json:"id"`
	URI    string `json:"runner_uri"`
	Origin origin `json:"origin"`
	Status string `json:"status"`
	Error  string `json:"error,omitempty"`
}

type report struct {
	Case         string            `json:"case"`
	GoVersion    string            `json:"go_version"`
	GodogVersion string            `json:"godog_version"`
	Markdown     string            `json:"markdown"`
	MarkdownHash string            `json:"markdown_sha256"`
	Blocks       int               `json:"gherkin_blocks"`
	Origins      map[string]origin `json:"scenario_origins"`
	Expected     []string          `json:"expected_scenarios"`
	Observed     []observation     `json:"observed_scenarios"`
	RunnerExit   *int              `json:"runner_exit"`
	GateAllowed  bool              `json:"gate_allowed"`
	Reasons      []string          `json:"gate_reasons"`
	FeatureFiles []string          `json:"feature_files_required"`
	InputMode    string            `json:"input_mode"`
	Transport    string            `json:"runner_transport"`
	FSOpens      int               `json:"filesystem_opens_memory_mode"`
}

var idPattern = regexp.MustCompile(`@SG-GO-SCN-[0-9]+`)

type rejectFS struct{ opens int }

func (f *rejectFS) Open(name string) (fs.File, error) {
	f.opens++
	return nil, fmt.Errorf("unexpected access to the runner filesystem: %s", name)
}

// extract uses Goldmark's AST, not a regular expression over Markdown fences.
// Leading blank lines preserve the Markdown line numbers in Godog's diagnostics.
func extract(source []byte, uri string) ([]godog.Feature, map[string]origin, error) {
	document := goldmark.New().Parser().Parse(text.NewReader(source))
	var features []godog.Feature
	origins := make(map[string]origin)
	block := 0
	err := ast.Walk(document, func(node ast.Node, entering bool) (ast.WalkStatus, error) {
		if !entering {
			return ast.WalkContinue, nil
		}
		fence, ok := node.(*ast.FencedCodeBlock)
		if !ok || string(fence.Language(source)) != "gherkin" {
			return ast.WalkContinue, nil
		}
		block++
		var content bytes.Buffer
		startLine := 1
		for i := 0; i < fence.Lines().Len(); i++ {
			segment := fence.Lines().At(i)
			line := bytes.Count(source[:segment.Start], []byte{'\n'}) + 1
			if i == 0 {
				startLine = line
			}
			value := segment.Value(source)
			content.Write(value)
			for _, tag := range idPattern.FindAllString(string(value), -1) {
				id := strings.TrimPrefix(tag, "@")
				if _, duplicate := origins[id]; duplicate {
					return ast.WalkStop, fmt.Errorf("duplicate ID: %s", id)
				}
				origins[id] = origin{Document: uri, Block: block, Line: line}
			}
		}
		padded := append(bytes.Repeat([]byte{'\n'}, startLine-1), content.Bytes()...)
		features = append(features, godog.Feature{
			Name:     fmt.Sprintf("%s#gherkin-%d", uri, block),
			Contents: padded,
		})
		return ast.WalkContinue, nil
	})
	return features, origins, err
}

func scenarioID(scenario *godog.Scenario) string {
	for _, tag := range scenario.Tags {
		if strings.HasPrefix(tag.Name, "@SG-GO-SCN-") {
			return strings.TrimPrefix(tag.Name, "@")
		}
	}
	return "<missing-id>"
}

func initialize(observed *[]observation, origins map[string]origin) func(*godog.ScenarioContext) {
	return func(sc *godog.ScenarioContext) {
		var a, b, result int
		var order Order
		sc.Before(func(ctx context.Context, scenario *godog.Scenario) (context.Context, error) {
			a, b, result = 0, 0, 0
			order = Order{}
			return ctx, nil
		})
		sc.After(func(ctx context.Context, scenario *godog.Scenario, err error) (context.Context, error) {
			id := scenarioID(scenario)
			item := observation{ID: id, URI: scenario.Uri, Origin: origins[id], Status: "passed"}
			if err != nil {
				item.Status = "not_passed"
				item.Error = err.Error()
			}
			*observed = append(*observed, item)
			return ctx, nil
		})
		sc.Step(`^os números (\d+) e (\d+)$`, func(x, y int) error { a, b = x, y; return nil })
		sc.Step(`^eu somar os números$`, func() error { result = Add(a, b); return nil })
		sc.Step(`^o resultado deve ser (\d+)$`, func(expected int) error {
			if result != expected {
				return fmt.Errorf("Add(%d, %d) = %d; expected %d", a, b, result, expected)
			}
			return nil
		})
		sc.Step(`^um pedido cancelado sem cobranças$`, func() error { order.Cancel(); return nil })
		sc.Step(`^o evento de cobrança for reprocessado$`, func() error { order.ReprocessChargeEvent(); return nil })
		sc.Step(`^nenhuma cobrança deve ser criada$`, func() error {
			if order.Charges != 0 {
				return fmt.Errorf("charges = %d; expected 0", order.Charges)
			}
			return nil
		})
		sc.Step(`^uma integração ainda pendente$`, func() error { return godog.ErrPending })
	}
}

func run() int {
	mode := flag.String("case", "pass", "pass, failure, undefined, pending, filtered, partial, zero, no-gherkin")
	input := flag.String("source", "contract.md", "Markdown file or - for stdin (our own adapter)")
	uri := flag.String("uri", "", "Markdown origin presented to the runner")
	transport := flag.String("transport", "bytes", "bytes, vfs or vfs-dir")
	flag.Parse()

	tags := "@pass"
	expected := []string{"SG-GO-SCN-001", "SG-GO-SCN-002"}
	switch *mode {
	case "pass":
	case "failure":
		tags, expected = "@failure", []string{"SG-GO-SCN-003"}
	case "undefined":
		tags, expected = "@undefined", []string{"SG-GO-SCN-004"}
	case "pending":
		tags, expected = "@pending", []string{"SG-GO-SCN-005"}
	case "filtered":
		tags = "@tag_inexistente"
	case "partial":
		tags = "@sum"
	case "zero":
		*input = "empty.md"
		tags = ""
	case "no-gherkin":
		*input = "reference.md"
		tags = ""
	default:
		fmt.Fprintln(os.Stderr, "invalid case:", *mode)
		return 2
	}
	if *uri == "" {
		*uri = *input
		if *uri == "-" {
			*uri = "stdin.md"
		}
	}
	var source []byte
	var err error
	inputMode := "file"
	if *input == "-" {
		inputMode = "stdin-adapter"
		source, err = io.ReadAll(os.Stdin)
	} else {
		source, err = os.ReadFile(*input)
	}
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		return 2
	}
	features, origins, err := extract(source, *uri)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		return 2
	}
	digest := sha256.Sum256(source)
	r := report{Case: *mode, GoVersion: runtime.Version(), GodogVersion: "v0.16.0", Markdown: *uri, MarkdownHash: hex.EncodeToString(digest[:]), Blocks: len(features), Origins: origins, Expected: expected, Observed: []observation{}, Reasons: []string{}, FeatureFiles: []string{}, InputMode: inputMode, Transport: *transport}
	if len(features) == 0 {
		r.Reasons = append(r.Reasons, "no Gherkin block; runner not invoked")
	} else {
		var log bytes.Buffer
		blockedFS := &rejectFS{}
		options := &godog.Options{Format: "pretty", NoColors: true, Strict: true, Concurrency: 1, Tags: tags, FeatureContents: features, FS: blockedFS, Output: &log}
		switch *transport {
		case "bytes":
		case "vfs", "vfs-dir":
			virtual := fstest.MapFS{}
			options.FeatureContents = nil
			options.Paths = []string{}
			for _, feature := range features {
				virtual[feature.Name] = &fstest.MapFile{Data: feature.Contents, Mode: 0444}
				options.Paths = append(options.Paths, feature.Name)
			}
			options.FS = virtual
			if *transport == "vfs-dir" {
				options.Paths = []string{"."}
			}
		default:
			fmt.Fprintln(os.Stderr, "invalid transport:", *transport)
			return 2
		}
		suite := godog.TestSuite{Name: "specmd-go-memory", ScenarioInitializer: initialize(&r.Observed, origins), Options: options}
		code := suite.Run()
		r.FSOpens = blockedFS.opens
		r.RunnerExit = &code
		fmt.Fprint(os.Stderr, log.String())
		if code != 0 {
			r.Reasons = append(r.Reasons, fmt.Sprintf("runner returned %d", code))
		}
	}
	seen := make(map[string]int)
	wanted := make(map[string]bool)
	for _, id := range expected {
		wanted[id] = true
	}
	for _, item := range r.Observed {
		seen[item.ID]++
		if !wanted[item.ID] {
			r.Reasons = append(r.Reasons, item.ID+" does not belong to the expected set")
		}
		if item.Status != "passed" {
			r.Reasons = append(r.Reasons, item.ID+" did not pass")
		}
	}
	for _, id := range expected {
		if seen[id] != 1 {
			r.Reasons = append(r.Reasons, fmt.Sprintf("%s executed %d time(s); required 1", id, seen[id]))
		}
	}
	if len(r.Observed) == 0 {
		r.Reasons = append(r.Reasons, "zero scenarios executed does not authorize completion")
	}
	sort.Slice(r.Observed, func(i, j int) bool { return r.Observed[i].ID < r.Observed[j].ID })
	r.GateAllowed = len(r.Reasons) == 0
	encoded, _ := json.MarshalIndent(r, "", "  ")
	fmt.Println(string(encoded))
	if !r.GateAllowed {
		return 1
	}
	return 0
}

func main() { os.Exit(run()) }
