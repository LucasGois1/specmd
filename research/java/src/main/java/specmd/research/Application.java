package specmd.research;

import java.util.concurrent.atomic.AtomicInteger;

/** Application code exercised by the real Cucumber step definitions. */
public final class Application {
    public static final AtomicInteger CALLS = new AtomicInteger();
    private Application() {}
    public static int add(int left, int right) {
        CALLS.incrementAndGet();
        return left + right;
    }
}
