package specmd.research;

import io.cucumber.core.feature.FeatureParser;
import io.cucumber.core.gherkin.Feature;
import io.cucumber.core.options.RuntimeOptionsBuilder;
import io.cucumber.core.resource.Resource;
import io.cucumber.plugin.ConcurrentEventListener;
import io.cucumber.plugin.event.EventPublisher;
import io.cucumber.plugin.event.TestCaseFinished;
import io.cucumber.plugin.event.TestStepFinished;
import io.cucumber.tagexpressions.TagExpressionParser;
import org.commonmark.node.AbstractVisitor;
import org.commonmark.node.FencedCodeBlock;
import org.commonmark.parser.IncludeSourceSpans;
import org.commonmark.parser.Parser;

import java.io.ByteArrayInputStream;
import java.io.InputStream;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.TimeUnit;
import java.util.regex.Pattern;

/** Research probe; not a production SpecMD verifier or acceptance authority. */
public final class Probe {
    private final Path root;
    private final List<Map<String, Object>> cases = new ArrayList<>();
    private boolean expectationsMet = true;

    private Probe(Path root) {
        this.root = root.toAbsolutePath().normalize();
    }

    private record Extraction(List<Feature> features, Set<String> requiredIds,
                              List<Map<String, Object>> blocks) {}

    private Extraction extract(String relative) throws Exception {
        String markdown = Files.readString(root.resolve(relative), StandardCharsets.UTF_8);
        var parser = Parser.builder().includeSourceSpans(IncludeSourceSpans.BLOCKS).build();
        List<Feature> features = new ArrayList<>();
        Set<String> ids = new LinkedHashSet<>();
        List<Map<String, Object>> blocks = new ArrayList<>();
        parser.parse(markdown).accept(new AbstractVisitor() {
            @Override public void visit(FencedCodeBlock block) {
                if (!"gherkin".equals(block.getInfo().trim())) return;
                int index = blocks.size() + 1;
                int openingLine = block.getSourceSpans().get(0).getLineIndex() + 1;
                // Leading blank lines align Gherkin locations with the original .md.
                String gherkin = "\n".repeat(openingLine) + block.getLiteral();
                URI uri = URI.create("specmd:///" + relative + "#block-" + index);
                byte[] bytes = gherkin.getBytes(StandardCharsets.UTF_8);
                Resource resource = new Resource() {
                    @Override public URI getUri() { return uri; }
                    @Override public InputStream getInputStream() {
                        return new ByteArrayInputStream(bytes);
                    }
                };
                Feature feature = new FeatureParser(UUID::randomUUID)
                    .parseResource(resource).orElseThrow(() -> new IllegalStateException("Empty block " + uri));
                features.add(feature);
                for (var pickle : feature.getPickles()) {
                    for (String tag : pickle.getTags()) {
                        if (tag.startsWith("@SMD-SCN-")) {
                            if (!ids.add(tag)) throw new IllegalStateException("Duplicate scenario ID " + tag);
                        }
                    }
                }
                blocks.add(Map.of("uri", uri.toString(), "opening_fence_line", openingLine,
                    "first_content_line", openingLine + 1, "scenario_count", feature.getPickles().size()));
            }
        });
        if (features.isEmpty() || ids.isEmpty()) throw new IllegalStateException("No executable scenarios: " + relative);
        int pickles = features.stream().mapToInt(f -> f.getPickles().size()).sum();
        if (pickles != ids.size()) throw new IllegalStateException("Every fixture scenario must have a unique ID");
        return new Extraction(features, ids, blocks);
    }

    private static final class Listener implements ConcurrentEventListener {
        final List<Map<String, Object>> results = new ArrayList<>();
        final Map<UUID, List<String>> stepStatuses = new LinkedHashMap<>();
        @Override public void setEventPublisher(EventPublisher publisher) {
            publisher.registerHandlerFor(TestStepFinished.class, event ->
                stepStatuses.computeIfAbsent(event.getTestCase().getId(), ignored -> new ArrayList<>())
                    .add(event.getResult().getStatus().name()));
            publisher.registerHandlerFor(TestCaseFinished.class, event -> {
                var testCase = event.getTestCase();
                Map<String, Object> row = new LinkedHashMap<>();
                row.put("scenario_ids", testCase.getTags().stream().filter(t -> t.startsWith("@SMD-SCN-")).toList());
                row.put("name", testCase.getName());
                row.put("uri", testCase.getUri().toString());
                row.put("line", testCase.getLocation().getLine());
                row.put("status", event.getResult().getStatus().name());
                row.put("step_statuses", stepStatuses.getOrDefault(testCase.getId(), List.of()));
                if (event.getResult().getError() != null) {
                    Throwable error = event.getResult().getError();
                    row.put("error", error.getClass().getSimpleName() + ": " + error.getMessage());
                }
                results.add(row);
            });
        }
    }

    private void runCase(String label, String relative, String tagFilter, boolean dryRun,
                         boolean expectedEligible, boolean expectedNativeSuccess) throws Exception {
        Extraction extraction = extract(relative);
        Listener listener = new Listener();
        RuntimeOptionsBuilder options = new RuntimeOptionsBuilder()
            .addGlue(URI.create("classpath:specmd/research"))
            .setMonochrome(true).setPublish(false).setPublishQuiet(true).setDryRun(dryRun);
        if (tagFilter != null) options.addTagFilter(TagExpressionParser.parse(tagFilter));
        Application.CALLS.set(0);
        io.cucumber.core.runtime.Runtime runtime = io.cucumber.core.runtime.Runtime.builder()
            .withRuntimeOptions(options.build())
            .withFeatureSupplier(() -> extraction.features())
            .withAdditionalPlugins(listener)
            .build();
        runtime.run();
        int nativeExit = runtime.exitStatus();
        int calls = Application.CALLS.get();
        Set<String> passedIds = new LinkedHashSet<>();
        for (Map<String, Object> result : listener.results) {
            @SuppressWarnings("unchecked") List<String> statuses = (List<String>) result.get("step_statuses");
            if ("PASSED".equals(result.get("status")) && !statuses.isEmpty()
                && statuses.stream().allMatch("PASSED"::equals)) {
                @SuppressWarnings("unchecked") List<String> resultIds = (List<String>) result.get("scenario_ids");
                passedIds.addAll(resultIds);
            }
        }
        // This fixture-specific predicate is deliberately stricter than Cucumber's exit code.
        // It is not an implementation of human approval or proof of arbitrary test quality.
        boolean eligible = !dryRun && nativeExit == 0
            && listener.results.size() == extraction.requiredIds().size()
            && passedIds.equals(extraction.requiredIds())
            && calls == extraction.requiredIds().size();
        List<String> markdownLines = Files.readAllLines(root.resolve(relative), StandardCharsets.UTF_8);
        boolean locationsConsistent = listener.results.stream().allMatch(result -> {
            int line = ((Number) result.get("line")).intValue();
            return line >= 1 && line <= markdownLines.size()
                && markdownLines.get(line - 1).contains("Cenário: " + result.get("name"))
                && result.get("uri").toString().startsWith("specmd:///" + relative + "#block-");
        });
        boolean asExpected = eligible == expectedEligible && (nativeExit == 0) == expectedNativeSuccess;
        asExpected &= locationsConsistent;
        if ("assertion_failure".equals(label)) asExpected &= listener.results.stream().anyMatch(r -> "FAILED".equals(r.get("status")));
        if ("undefined_step".equals(label)) asExpected &= listener.results.stream().anyMatch(r -> "UNDEFINED".equals(r.get("status")));
        expectationsMet &= asExpected;
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("case", label);
        row.put("fixture", relative);
        row.put("blocks", extraction.blocks());
        row.put("required_scenario_ids", extraction.requiredIds());
        row.put("native_runner_exit_code", nativeExit);
        row.put("finished_scenarios", listener.results.size());
        row.put("application_function_calls", calls);
        row.put("dry_run", dryRun);
        row.put("tag_filter", tagFilter);
        row.put("scenario_results", listener.results);
        row.put("source_locations_checked", listener.results.size());
        row.put("source_locations_consistent", locationsConsistent);
        row.put("research_gate_eligible", eligible);
        row.put("expected_gate_eligible", expectedEligible);
        row.put("harness_expectations_met", asExpected);
        cases.add(row);
        System.out.println("CASE " + label + " native=" + nativeExit + " finished=" + listener.results.size()
            + " app_calls=" + calls + " gate=" + eligible + " expectations=" + asExpected);
    }

    private Map<String, Object> cliCase(String label, String stdin, List<String> tail) throws Exception {
        List<String> command = new ArrayList<>(List.of(
            Path.of(System.getProperty("java.home"), "bin", "java").toString(),
            "-cp", System.getProperty("java.class.path"), "io.cucumber.core.cli.Main",
            "--glue", "specmd.research", "--plugin", "specmd.research.CliCounter", "--no-summary"));
        command.addAll(tail);
        ProcessBuilder builder = new ProcessBuilder(command).directory(root.toFile()).redirectErrorStream(true);
        builder.environment().put("CUCUMBER_PUBLISH_ENABLED", "false");
        builder.environment().put("CUCUMBER_PUBLISH_QUIET", "true");
        Process process = builder.start();
        process.getOutputStream().write(stdin.getBytes(StandardCharsets.UTF_8));
        process.getOutputStream().close();
        boolean completed = process.waitFor(15, TimeUnit.SECONDS);
        if (!completed) process.destroyForcibly().waitFor();
        String output = new String(process.getInputStream().readAllBytes(), StandardCharsets.UTF_8)
            .replace(root.toString(), "[PROJECT]");
        if (output.length() > 8000) output = output.substring(0, 8000) + "\n[truncated]";
        var matcher = Pattern.compile("SPECMD_CLI_COUNTS finished=(\\d+) application_calls=(\\d+)").matcher(output);
        Integer finished = null;
        Integer calls = null;
        if (matcher.find()) { finished = Integer.parseInt(matcher.group(1)); calls = Integer.parseInt(matcher.group(2)); }
        boolean noScenarioExecution = finished == null || finished == 0;
        boolean asExpected = completed && noScenarioExecution;
        expectationsMet &= asExpected;
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("case", label);
        row.put("actually_executed", true);
        row.put("main_class", "io.cucumber.core.cli.Main");
        row.put("tail_arguments", tail);
        row.put("stdin_supplied", !stdin.isEmpty());
        row.put("native_cli_exit_code", process.exitValue());
        row.put("timed_out", !completed);
        row.put("finished_scenarios", finished);
        row.put("application_function_calls", calls);
        row.put("output", output);
        row.put("harness_expectations_met", asExpected);
        System.out.println("CLI " + label + " native=" + process.exitValue() + " finished=" + finished + " expectations=" + asExpected);
        return row;
    }

    private long featureFileCount() throws Exception {
        try (var paths = Files.walk(root)) {
            return paths.filter(Files::isRegularFile).filter(p -> p.toString().endsWith(".feature")).count();
        }
    }

    private static String json(Object value) {
        if (value == null) return "null";
        if (value instanceof Boolean || value instanceof Number) return value.toString();
        if (value instanceof Map<?, ?> map) {
            List<String> parts = new ArrayList<>();
            map.forEach((key, item) -> parts.add(json(key.toString()) + ":" + json(item)));
            return "{" + String.join(",", parts) + "}";
        }
        if (value instanceof Iterable<?> items) {
            List<String> parts = new ArrayList<>();
            for (Object item : items) parts.add(json(item));
            return "[" + String.join(",", parts) + "]";
        }
        String text = value.toString();
        StringBuilder escaped = new StringBuilder("\"");
        for (char c : text.toCharArray()) {
            if (c == '"') escaped.append("\\\"");
            else if (c == '\\') escaped.append("\\\\");
            else if (c == '\n') escaped.append("\\n");
            else if (c == '\r') escaped.append("\\r");
            else if (c == '\t') escaped.append("\\t");
            else if (c < 32) escaped.append(String.format("\\u%04x", (int)c));
            else escaped.append(c);
        }
        return escaped.append('"').toString();
    }

    public static void main(String[] args) throws Exception {
        Probe probe = new Probe(Path.of(args.length > 0 ? args[0] : "."));
        long before = probe.featureFileCount();
        probe.runCase("passing_two_blocks_pt", "fixtures/passing.md", null, false, true, true);
        probe.runCase("assertion_failure", "fixtures/failing.md", null, false, false, false);
        probe.runCase("undefined_step", "fixtures/undefined.md", null, false, false, false);
        probe.runCase("all_required_scenarios_filtered", "fixtures/passing.md", "@does_not_exist", false, false, true);
        probe.runCase("dry_run_without_application_execution", "fixtures/passing.md", null, true, false, true);

        String plain = "# language: pt\nFuncionalidade: CLI texto\n  Cenário: Soma\n    Dado os números 2 e 3\n    Quando a aplicação somar os números\n    Então o resultado deve ser 5\n";
        List<Map<String, Object>> cli = new ArrayList<>();
        cli.add(probe.cliCase("text_argument", "", List.of(plain)));
        cli.add(probe.cliCase("stdin_dash", plain, List.of("-")));
        cli.add(probe.cliCase("stdin_without_path", plain, List.of()));
        cli.add(probe.cliCase("markdown_path", "", List.of("fixtures/passing.md")));
        long after = probe.featureFileCount();
        probe.expectationsMet &= before == 0 && after == 0;

        Map<String, Object> checksums = new LinkedHashMap<>();
        for (String fixture : List.of("fixtures/passing.md", "fixtures/failing.md", "fixtures/undefined.md")) {
            checksums.put(fixture, HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(probe.root.resolve(fixture)))));
        }
        Map<String, Object> report = new LinkedHashMap<>();
        report.put("status", "executed");
        report.put("observed_at_utc", Instant.now().toString());
        report.put("versions", Map.of("cucumber_jvm", "8.0.4", "commonmark", "0.24.0", "java", System.getProperty("java.version")));
        report.put("reproduction_command", "bash run.sh");
        report.put("fixture_sha256", checksums);
        report.put("feature_files_before", before);
        report.put("feature_files_after", after);
        report.put("api_cases", probe.cases);
        report.put("cli_cases", cli);
        report.put("harness_expectations_met", probe.expectationsMet);
        report.put("harness_exit_code", probe.expectationsMet ? 0 : 1);
        report.put("human_approval_implemented", false);
        report.put("production_gate_implemented", false);
        Path output = probe.root.resolve(args.length > 1 ? args[1] : "evidence/results.json");
        Files.createDirectories(output.getParent());
        Files.writeString(output, json(report) + "\n", StandardCharsets.UTF_8);
        System.out.println("HARNESS expectations=" + probe.expectationsMet + " feature_files=" + before + "->" + after);
        if (!probe.expectationsMet) System.exit(1);
    }
}
