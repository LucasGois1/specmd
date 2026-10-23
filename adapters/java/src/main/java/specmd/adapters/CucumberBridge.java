package specmd.adapters;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.google.gson.Strictness;
import com.google.gson.stream.JsonReader;
import io.cucumber.core.feature.FeatureParser;
import io.cucumber.core.feature.GluePath;
import io.cucumber.core.gherkin.Feature;
import io.cucumber.core.options.RuntimeOptionsBuilder;
import io.cucumber.core.resource.Resource;
import io.cucumber.gherkin.GherkinDialects;
import io.cucumber.messages.types.Envelope;
import io.cucumber.plugin.ConcurrentEventListener;
import io.cucumber.plugin.event.EventPublisher;
import io.cucumber.plugin.event.PickleStepTestStep;
import io.cucumber.plugin.event.TestCaseFinished;
import io.cucumber.plugin.event.TestStepFinished;

import java.io.ByteArrayInputStream;
import java.io.InputStream;
import java.io.PrintStream;
import java.io.StringReader;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;

/** Experimental JSON bridge. Executes real Cucumber steps, not human acceptance. */
public final class CucumberBridge {
    private static final Gson JSON = new GsonBuilder().disableHtmlEscaping().serializeNulls().create();
    private record Origin(String id, String path, int block, int line) {}
    private record Declaration(Origin origin, URI uri, int steps) {}
    private record Prepared(List<Feature> features, Map<String, Declaration> declarations) {}

    private static String text(JsonObject object, String key) {
        JsonElement value = object.get(key);
        if (value == null || !value.isJsonPrimitive() || !value.getAsJsonPrimitive().isString()
            || value.getAsString().isEmpty()) throw new IllegalArgumentException("Invalid string: " + key);
        return value.getAsString();
    }
    private static int integer(JsonObject object, String key) {
        JsonElement value = object.get(key);
        if (value == null || !value.isJsonPrimitive() || !value.getAsJsonPrimitive().isNumber())
            throw new IllegalArgumentException("Invalid integer: " + key);
        return value.getAsBigDecimal().intValueExact();
    }
    private static JsonArray array(JsonObject object, String key) {
        JsonElement value = object.get(key);
        if (value == null || !value.isJsonArray()) throw new IllegalArgumentException("Invalid array: " + key);
        return value.getAsJsonArray();
    }
    private static Origin origin(JsonObject object) {
        Origin result = new Origin(text(object,"id"),text(object,"path"),integer(object,"block"),integer(object,"line"));
        if (result.block()<1 || result.line()<1) throw new IllegalArgumentException("Invalid scenario origin");
        return result;
    }
    /** Scenarios are matched by their place in the Markdown; IDs are opaque. */
    private static String key(String path,int block,int line){return path+"#"+block+":"+line;}

    private static Prepared prepare(JsonObject input) throws Exception {
        if (integer(input,"schema") != 1) throw new IllegalArgumentException("Only bridge schema 1 is supported");
        JsonArray blocks=array(input,"features"), expected=array(input,"expected_scenarios");
        if (blocks.isEmpty() || expected.isEmpty()) throw new IllegalArgumentException("Features and expected scenarios must be nonempty");
        Map<String,Origin> wanted=new LinkedHashMap<>();
        Map<String,Boolean> ids=new LinkedHashMap<>();
        for (JsonElement value:expected) {
            Origin item=origin(value.getAsJsonObject());
            if (wanted.putIfAbsent(key(item.path(),item.block(),item.line()),item)!=null || ids.putIfAbsent(item.id(),true)!=null)
                throw new IllegalArgumentException("Duplicate expected scenario: "+item.id());
        }
        List<Feature> features=new ArrayList<>();
        Map<String,Declaration> declarations=new LinkedHashMap<>();
        Map<URI,Boolean> uris=new LinkedHashMap<>();
        for (JsonElement value:blocks) {
            JsonObject block=value.getAsJsonObject();
            String path=text(block,"path"), content=text(block,"content");
            int index=integer(block,"block"), line=integer(block,"line");
            if (index<1 || line<1 || line>1_000_000) throw new IllegalArgumentException("Invalid block/line");
            URI uri=new URI("specmd","","/"+path,null,"block-"+index);
            if (uris.putIfAbsent(uri,true)!=null) throw new IllegalArgumentException("Duplicate block: "+uri);
            byte[] bytes=("\n".repeat(line-1)+content).getBytes(StandardCharsets.UTF_8);
            Resource resource=new Resource() {
                public URI getUri(){return uri;}
                public InputStream getInputStream(){return new ByteArrayInputStream(bytes);}
            };
            Feature feature=new FeatureParser(UUID::randomUUID).parseResource(resource)
                .orElseThrow(()->new IllegalArgumentException("Empty feature: "+uri));
            boolean foundAst=false;
            for (Object event:feature.getParseEvents()) {
                if (!(event instanceof Envelope envelope) || envelope.getGherkinDocument().isEmpty()
                    || envelope.getGherkinDocument().get().getFeature().isEmpty()) continue;
                foundAst=true;
                var ast=envelope.getGherkinDocument().get().getFeature().get();
                var dialect=GherkinDialects.getDialect(ast.getLanguage()).orElseThrow();
                int backgrounds=ast.getChildren().stream().flatMap(child->child.getBackground().stream())
                    .mapToInt(background->background.getSteps().size()).sum();
                for (var child:ast.getChildren()) {
                    if (child.getRule().isPresent()) throw new IllegalArgumentException("Unsupported: Rule requires rule-aware evidence");
                    if (child.getScenario().isEmpty()) continue;
                    var scenario=child.getScenario().get();
                    if (!scenario.getExamples().isEmpty() || dialect.getScenarioOutlineKeywords().contains(scenario.getKeyword()))
                        throw new IllegalArgumentException("Unsupported: Scenario Outline requires concrete instance evidence");
                    if (scenario.getSteps().isEmpty()) throw new IllegalArgumentException("Each simple scenario requires steps");
                    int scenarioLine=Math.toIntExact(scenario.getLocation().getLine());
                    Origin actual=wanted.get(key(path,index,scenarioLine));
                    if (actual==null) throw new IllegalArgumentException("Unexpected scenario at "+path+":"+scenarioLine);
                    if (declarations.putIfAbsent(actual.id(),new Declaration(actual,uri,backgrounds+scenario.getSteps().size()))!=null)
                        throw new IllegalArgumentException("Duplicate scenario: "+actual.id());
                }
            }
            if (!foundAst) throw new IllegalArgumentException("No Gherkin AST for "+uri);
            features.add(feature);
        }
        if (declarations.size()!=wanted.size()) throw new IllegalArgumentException("Declared and expected scenario sets differ");
        return new Prepared(features,declarations);
    }

    private static String status(String nativeStatus) {
        String value=nativeStatus.toLowerCase(Locale.ROOT);
        return List.of("passed","failed","undefined","skipped","pending").contains(value)?value:"failed";
    }

    private static final class Listener implements ConcurrentEventListener {
        final Map<UUID,List<Map<String,Object>>> steps=new LinkedHashMap<>();
        final List<Map<String,Object>> scenarios=new ArrayList<>();
        final Map<String,Declaration> declared;
        final List<String> errors=new ArrayList<>();
        final Map<String,String> byLocation=new LinkedHashMap<>();
        Listener(Map<String,Declaration> declared){
            this.declared=declared;
            declared.forEach((id,declaration)->byLocation.put(declaration.uri()+":"+declaration.origin().line(),id));
        }
        public void setEventPublisher(EventPublisher publisher) {
            publisher.registerHandlerFor(TestStepFinished.class,event->{
                if (!(event.getTestStep() instanceof PickleStepTestStep step)) return;
                Map<String,Object> result=new LinkedHashMap<>();
                result.put("status",status(event.getResult().getStatus().name()));
                result.put("text",step.getStep().getText());result.put("line",step.getStep().getLine());
                steps.computeIfAbsent(event.getTestCase().getId(),ignored->new ArrayList<>()).add(result);
            });
            publisher.registerHandlerFor(TestCaseFinished.class,event->{
                var testCase=event.getTestCase();
                String id=byLocation.get(testCase.getUri()+":"+testCase.getLocation().getLine());
                if (id==null) {errors.add("Runtime scenario has no expected origin");return;}
                Declaration declaration=declared.get(id);
                if (declaration==null || !declaration.uri().equals(testCase.getUri())
                    || declaration.origin().line()!=testCase.getLocation().getLine()) {
                    errors.add("Runtime origin mismatch: "+id);return;
                }
                var observed=steps.getOrDefault(testCase.getId(),List.of());
                long executed=observed.stream().filter(step->List.of("passed","failed","pending").contains(step.get("status"))).count();
                Map<String,Object> result=new LinkedHashMap<>();Origin origin=declaration.origin();
                result.put("id",id);result.put("path",origin.path());result.put("block",origin.block());result.put("line",origin.line());
                String finalStatus=status(event.getResult().getStatus().name());
                if (finalStatus.equals("passed") && (executed==0 || observed.size()!=declaration.steps()
                    || observed.stream().anyMatch(step->!"passed".equals(step.get("status"))))) finalStatus="failed";
                result.put("status",finalStatus);result.put("steps_executed",executed);result.put("steps",observed);
                scenarios.add(result);
            });
        }
    }

    private static Map<String,Object> report(JsonObject input,List<String> glue) throws Exception {
        Prepared prepared=prepare(input);Listener listener=new Listener(prepared.declarations());
        if (glue.isEmpty()) throw new IllegalArgumentException("At least one --glue package is required");
        RuntimeOptionsBuilder options=new RuntimeOptionsBuilder().setDryRun(false).setMonochrome(true)
            .setPublish(false).setPublishQuiet(true).setThreads(1);
        for(String value:glue) options.addGlue(GluePath.parse(value));
        var runtime=io.cucumber.core.runtime.Runtime.builder().withRuntimeOptions(options.build())
            .withFeatureSupplier(prepared::features).withAdditionalPlugins(listener).build();
        runtime.run();
        boolean failed=runtime.exitStatus()!=0;
        Map<String,Integer> seen=new LinkedHashMap<>();
        boolean passed=!failed && listener.errors.isEmpty() && listener.scenarios.size()==prepared.declarations().size()
            && !listener.scenarios.isEmpty();
        for(var row:listener.scenarios) {
            String id=row.get("id").toString();seen.merge(id,1,Integer::sum);
            if (!"passed".equals(row.get("status")) || ((Number)row.get("steps_executed")).intValue()<1) passed=false;
        }
        for(String id:prepared.declarations().keySet()) if(seen.getOrDefault(id,0)!=1) {
            passed=false;listener.errors.add(id+" was not executed exactly once");
        }
        Map<String,Object> result=base();result.put("engine_failed",failed);result.put("passed",passed);
        result.put("scenarios",listener.scenarios);result.put("errors",listener.errors);return result;
    }

    private static Map<String,Object> base() {
        Map<String,Object> result=new LinkedHashMap<>();
        result.put("schema",1);result.put("mode","real");result.put("dry_run",false);result.put("engine_failed",true);
        result.put("scenarios",List.of());result.put("passed",false);return result;
    }

    public static void main(String[] args) {
        PrintStream protocol=System.out;
        Map<String,Object> result=base();
        try {
            List<String> glue=new ArrayList<>();
            for(int i=0;i<args.length;i++) {
                if (!args[i].equals("--glue") || i+1>=args.length) throw new IllegalArgumentException("Usage: --glue package [--glue package]");
                glue.add(args[++i]);
            }
            byte[] bytes=System.in.readNBytes(8*1024*1024+1);
            if(bytes.length>8*1024*1024) throw new IllegalArgumentException("Input exceeds 8 MiB");
            JsonReader reader=new JsonReader(new StringReader(new String(bytes,StandardCharsets.UTF_8)));
            reader.setStrictness(Strictness.STRICT);
            JsonObject input=JsonParser.parseReader(reader).getAsJsonObject();
            if(reader.peek()!=com.google.gson.stream.JsonToken.END_DOCUMENT) throw new IllegalArgumentException("Expected one JSON input object");
            System.setOut(System.err);
            result=report(input,glue);
        } catch(Exception error) {
            result=base();result.put("errors",List.of(error.getClass().getSimpleName()+": "+error.getMessage()));
        } finally {
            System.setOut(protocol);
        }
        protocol.println(JSON.toJson(result));
        if(!Boolean.TRUE.equals(result.get("passed"))) System.exit(1);
    }
}
