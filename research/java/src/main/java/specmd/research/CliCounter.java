package specmd.research;

import io.cucumber.plugin.ConcurrentEventListener;
import io.cucumber.plugin.event.EventPublisher;
import io.cucumber.plugin.event.TestCaseFinished;
import io.cucumber.plugin.event.TestRunFinished;

/** Counts actual scenario completions in separately launched, real CLI processes. */
public final class CliCounter implements ConcurrentEventListener {
    private int finished;
    @Override public void setEventPublisher(EventPublisher publisher) {
        publisher.registerHandlerFor(TestCaseFinished.class, event -> finished++);
        publisher.registerHandlerFor(TestRunFinished.class, event -> System.out.println(
            "SPECMD_CLI_COUNTS finished=" + finished + " application_calls=" + Application.CALLS.get()));
    }
}
