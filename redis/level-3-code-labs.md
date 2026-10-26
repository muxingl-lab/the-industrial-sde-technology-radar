# Redis Source Study — Level 3: Code Labs

[Radar home](../README.md) · [Redis home](README.md) · [Level 1](level-1-philosophy.md) · [Level 2](level-2-internals.md)

These are mechanism-sized implementations, not production replacements for Redis. Unless a C/OS primitive is essential, examples use Java so the invariants remain visible.

## Q1. Incremental hash map

[Philosophy](level-1-philosophy.md#q1-how-do-you-prevent-a-large-maintenance-operation-from-destroying-tail-latency) · [Interview answer](level-2-internals.md#q1-incremental-work)

```java
final class IncrementalMap<K, V> {
    private Entry<K, V>[] oldTable;
    private Entry<K, V>[] newTable;
    private int rehashIndex;

    V get(K key) {
        V value = find(newTable, key);
        return value != null ? value : find(oldTable, key);
    }

    void put(K key, V value) {
        rehashStep(1);
        removeFrom(oldTable, key);       // one authoritative copy
        putInto(activeTable(), key, value);
        if (newTable == null && loadFactor(oldTable) > 0.75) {
            newTable = allocate(oldTable.length * 2);
            rehashIndex = 0;
        }
    }

    void rehashStep(int nonEmptyBuckets) {
        if (newTable == null) return;
        int emptyBudget = nonEmptyBuckets * 10;
        while (nonEmptyBuckets > 0 && rehashIndex < oldTable.length) {
            Entry<K, V> chain = oldTable[rehashIndex];
            oldTable[rehashIndex++] = null;
            if (chain == null) {
                if (--emptyBudget == 0) break;
                continue;
            }
            while (chain != null) {
                Entry<K, V> next = chain.next;
                putInto(newTable, chain.key, chain.value);
                chain = next;
            }
            nonEmptyBuckets--;
        }
        if (rehashIndex == oldTable.length) {
            oldTable = newTable;
            newTable = null;
        }
    }
}
```

**Handwrite:** implement `remove`, including a key that may live in either table. Then design an iterator and state whether it pauses migration, stores server-side state, or permits duplicates.

**Invariant test:** after every randomized operation, compare content with `java.util.HashMap` and assert that a key never exists in both tables.

## Q2. Adaptive integer set

[Philosophy](level-1-philosophy.md#q2-when-should-one-logical-data-type-have-several-physical-representations) · [Interview answer](level-2-internals.md#q2-adaptive-representation)

```java
sealed interface IntSet permits PackedIntSet, HashedIntSet {
    boolean contains(int value);
    IntSet add(int value);       // may return an upgraded representation
    int size();
}

final class PackedIntSet implements IntSet {
    private int[] sorted;
    private int size;
    private static final int UPGRADE_AT = 128;

    public boolean contains(int value) {
        return Arrays.binarySearch(sorted, 0, size, value) >= 0;
    }

    public IntSet add(int value) {
        int at = Arrays.binarySearch(sorted, 0, size, value);
        if (at >= 0) return this;
        if (size == UPGRADE_AT) {
            HashedIntSet upgraded = new HashedIntSet(size * 2);
            for (int i = 0; i < size; i++) upgraded.add(sorted[i]);
            return upgraded.add(value);
        }
        at = -at - 1;
        ensureCapacity(size + 1);
        System.arraycopy(sorted, at, sorted, at + 1, size - at);
        sorted[at] = value;
        size++;
        return this;
    }
}
```

**Handwrite:** replace `int[]` with a byte buffer that upgrades from 16-bit to 32-bit to 64-bit storage. Check overflow before conversion and calculate temporary peak memory.

**Benchmark:** compare bytes/item and lookup latency against `HashSet<Integer>` for N = 8, 32, 128, and 1,024.

## Q3. Dual-index ranked set

[Philosophy](level-1-philosophy.md#q3-what-should-you-do-when-one-data-set-must-support-incompatible-access-patterns) · [Interview answer](level-2-internals.md#q3-multiple-access-paths)

```java
record RankedKey(double score, String member)
        implements Comparable<RankedKey> {
    public int compareTo(RankedKey other) {
        int byScore = Double.compare(score, other.score);
        return byScore != 0 ? byScore : member.compareTo(other.member);
    }
}

final class RankedSet {
    private final Map<String, Double> scoreByMember = new HashMap<>();
    private final NavigableSet<RankedKey> ordered = new TreeSet<>();

    void put(String member, double score) {
        Double old = scoreByMember.get(member);
        if (old != null) ordered.remove(new RankedKey(old, member));
        ordered.add(new RankedKey(score, member));
        scoreByMember.put(member, score);
        assert scoreByMember.size() == ordered.size();
    }

    void remove(String member) {
        Double score = scoreByMember.remove(member);
        if (score != null && !ordered.remove(new RankedKey(score, member))) {
            throw new IllegalStateException("indexes diverged");
        }
    }
}
```

**Handwrite:** implement `rangeByScore`, `rank`, and crash-safe rebuilding of `ordered` from the authoritative map. For Redis fidelity, replace the tree with a skip list augmented with span counts.

## Q4. Sampled eviction

[Philosophy](level-1-philosophy.md#q4-when-is-an-approximate-answer-the-correct-engineering-answer) · [Interview answer](level-2-internals.md#q4-approximation)

```java
K chooseVictim(List<K> keys, ToLongFunction<K> lastAccess, int samples,
               ThreadLocalRandom random) {
    K victim = null;
    long oldest = Long.MAX_VALUE;
    for (int i = 0; i < samples; i++) {
        K candidate = keys.get(random.nextInt(keys.size()));
        long access = lastAccess.applyAsLong(candidate);
        if (access < oldest) {
            oldest = access;
            victim = candidate;
        }
    }
    return victim;
}

int probabilisticIncrement(int counter, int max, double logFactor) {
    if (counter >= max) return max;
    double probability = 1.0 / (1.0 + (counter * logFactor));
    return ThreadLocalRandom.current().nextDouble() < probability
            ? counter + 1 : counter;
}
```

**Handwrite:** add time decay and a persistent candidate pool. Simulate Zipfian traffic and compare hit rate for sample sizes 1, 5, 10, and exact LRU.

## Q5. Deferred free

[Philosophy](level-1-philosophy.md#q5-how-do-you-remove-a-large-object-without-making-deletion-a-long-request) · [Interview answer](level-2-internals.md#q5-deferred-reclamation)

```java
final class DeferredReclaimer implements AutoCloseable {
    private final BlockingQueue<DetachedValue> queue =
            new ArrayBlockingQueue<>(10_000);
    private final ExecutorService worker = Executors.newSingleThreadExecutor();

    DeferredReclaimer() {
        worker.submit(() -> {
            while (!Thread.currentThread().isInterrupted()) {
                DetachedValue value = queue.take();
                value.releaseOwnedResources();
            }
            return null;
        });
    }

    void delete(Map<String, DetachedValue> owner, String key) {
        DetachedValue detached = owner.remove(key); // visibility boundary
        if (detached == null) return;
        if (detached.estimatedFreeWork() < 64) detached.releaseOwnedResources();
        else if (!queue.offer(detached)) detached.releaseOwnedResources();
    }
}
```

**Handwrite:** add queued-byte accounting, overload policy, graceful shutdown, and a test proving the detached object cannot be reached or freed twice.

## Q6. Owner and worker

[Philosophy](level-1-philosophy.md#q6-how-can-a-mostly-single-threaded-system-safely-use-background-threads) · [Interview answer](level-2-internals.md#q6-state-ownership)

```java
record Work(long generation, byte[] immutableInput) {}
record Completion(long generation, byte[] output, Throwable error) {}

final class OwnerLoop {
    private final Map<String, byte[]> state = new HashMap<>();
    private final BlockingQueue<Completion> completions = new LinkedBlockingQueue<>();
    private final ExecutorService workers = Executors.newFixedThreadPool(4);
    private long generation;

    void submitPureWork(byte[] input) {
        Work work = new Work(generation, input.clone());
        workers.submit(() -> {
            try { completions.add(new Completion(work.generation(), compute(work.immutableInput()), null)); }
            catch (Throwable t) { completions.add(new Completion(work.generation(), null, t)); }
        });
    }

    void applyCompletions() { // owner thread only
        for (Completion c; (c = completions.poll()) != null;) {
            if (c.generation() != generation || c.error() != null) continue;
            state.put("result", c.output());
        }
    }
}
```

**Handwrite:** add cancellation and backpressure. Explain why a generation check is needed after configuration changes or failover.

## Q7. Hybrid expiration

[Philosophy](level-1-philosophy.md#q7-how-should-a-system-delete-expired-data-that-nobody-reads) · [Interview answer](level-2-internals.md#q7-expiration)

```java
V get(K key, long nowMillis) {
    DeadlineValue<V> value = data.get(key);
    if (value == null) return null;
    if (value.deadlineMillis() <= nowMillis) {
        data.remove(key, value); // expire on access
        return null;
    }
    return value.payload();
}

void activeExpire(long budgetNanos, int sampleSize) {
    long deadline = System.nanoTime() + budgetNanos;
    do {
        int sampled = 0, expired = 0;
        for (K key : randomKeys(sampleSize)) {
            sampled++;
            if (get(key, wallClock.millis()) == null) expired++;
            if (System.nanoTime() >= deadline) return;
        }
        if (sampled == 0 || expired * 100 / sampled <= 10) return;
    } while (System.nanoTime() < deadline);
}
```

**Handwrite:** replace random sampling with deadline buckets or a timing wheel. Define behavior for wall-clock rollback and a million keys sharing one deadline.

## Q8. Snapshot state machine

[Philosophy](level-1-philosophy.md#q8-how-can-an-in-memory-service-create-a-consistent-snapshot-while-continuing-to-serve-writes) · [Interview answer](level-2-internals.md#q8-copy-on-write-snapshot)

```text
IDLE
  | request snapshot
  v
FORKING --fork failure--> IDLE + alert
  | child created
  +--> PARENT_SERVING_WRITES
  |
  +--> CHILD_WRITING_TEMP
          | write/fsync/checksum failure --> discard temp
          v
      CHILD_SUCCESS
          | parent verifies generation and atomically renames
          v
        IDLE
```

```c
pid_t pid = fork();
if (pid == 0) {
    int fd = open(temp_path, O_CREAT | O_EXCL | O_WRONLY, 0600);
    write_snapshot_and_checksum(fd, state_visible_at_fork);
    fsync(fd);
    close(fd);
    _exit(0);
}
/* Parent keeps serving; later waitpid(), validate, rename(), fsync directory. */
```

**Handwrite:** enumerate crash points and state which file recovery selects after each. Explain why directory fsync may matter after rename.

## Q9. Log rewrite

[Philosophy](level-1-philosophy.md#q9-how-do-you-keep-an-append-only-history-from-growing-forever) · [Interview answer](level-2-internals.md#q9-log-compaction)

```java
record RewriteBoundary(long generation, long offset) {}

void rewrite() throws IOException {
    RewriteBoundary boundary = log.captureBoundary();
    Path temp = createNewGeneration();
    writeCanonicalState(temp, snapshotAt(boundary));
    appendTail(temp, log.readAfter(boundary.offset()));
    fsync(temp);
    validate(temp);
    atomicallyInstallManifest(temp, boundary.generation() + 1);
}
```

**Handwrite:** close the race between reading the tail and switching generations. A valid answer may briefly pause appends, use a double buffer, or perform a final synchronized tail copy.

## Q10. Bounded replay log

[Philosophy](level-1-philosophy.md#q10-how-should-a-replica-recover-after-a-short-disconnection) · [Interview answer](level-2-internals.md#q10-incremental-recovery)

```java
record ResumeRequest(UUID producerId, long nextOffset) {}
sealed interface ResumePlan {}
record Replay(List<Block> blocks, long skipBytes) implements ResumePlan {}
record FullSnapshot(Path snapshot, UUID producerId, long baseOffset) implements ResumePlan {}

ResumePlan resume(ResumeRequest request) {
    if (!request.producerId().equals(currentProducerId)) return newSnapshot();
    long first = backlog.firstOffset();
    long endExclusive = backlog.endOffset();
    if (request.nextOffset() < first || request.nextOffset() > endExclusive) {
        return newSnapshot();
    }
    return backlog.sliceFrom(request.nextOffset());
}
```

**Handwrite:** implement a segmented ring buffer with a sparse `NavigableMap<Long, Block>` index and incremental trimming. Test requests at `first - 1`, `first`, `end`, and `end + 1`.

## Q11. Bounded output buffer

[Philosophy](level-1-philosophy.md#q11-what-should-happen-when-a-consumer-is-slower-than-a-producer) · [Interview answer](level-2-internals.md#q11-backpressure)

```java
final class ClientBuffer {
    private final long hardBytes;
    private final long softBytes;
    private final Duration softDuration;
    private long bytes;
    private Instant softLimitSince;

    Decision onEnqueue(int addedBytes, Instant now) {
        bytes += addedBytes;
        if (bytes > hardBytes) return Decision.DISCONNECT;
        if (bytes > softBytes) {
            if (softLimitSince == null) softLimitSince = now;
            if (Duration.between(softLimitSince, now).compareTo(softDuration) > 0)
                return Decision.DISCONNECT;
        } else {
            softLimitSince = null;
        }
        return Decision.ACCEPT;
    }
}
```

**Handwrite:** add dequeue accounting and integer-overflow checks. Design distinct policies for interactive clients, replicas, and lossy subscriptions.

## Q12. Slot router

[Philosophy](level-1-philosophy.md#q12-how-do-you-repartition-a-live-keyspace) · [Interview answer](level-2-internals.md#q12-online-resharding)

```java
final class SlotRouter {
    private final Node[] ownerBySlot = new Node[16_384];

    Node route(byte[] key) {
        byte[] hashInput = hashTagOrWholeKey(key);
        int slot = crc16(hashInput) & 0x3fff;
        return ownerBySlot[slot];
    }

    Reply execute(Command command) {
        for (int attempts = 0; attempts < 3; attempts++) {
            Node node = route(command.key());
            Reply reply = node.send(command);
            if (reply instanceof Moved moved) {
                ownerBySlot[moved.slot()] = moved.permanentOwner();
                continue;
            }
            if (reply instanceof Ask ask) {
                return ask.temporaryOwner().sendAskingThen(command);
            }
            return reply;
        }
        throw new TopologyUnstableException();
    }
}
```

**Handwrite:** ensure two keys share a slot, bound redirect loops, refresh topology, and preserve the distinction between temporary `ASK` and permanent `MOVED`.

## Q13. Suspicion tracker

[Philosophy](level-1-philosophy.md#q13-how-should-a-distributed-system-decide-that-a-node-has-failed) · [Interview answer](level-2-internals.md#q13-failure-suspicion)

```java
final class SuspicionTracker {
    private final Map<NodeId, Instant> localTimeout = new HashMap<>();
    private final Map<NodeId, Map<ReporterId, Instant>> reports = new HashMap<>();

    Status status(NodeId target, Instant now, Set<ReporterId> eligibleMasters) {
        boolean locallySuspected = isRecent(localTimeout.get(target), now);
        long votes = reports.getOrDefault(target, Map.of()).entrySet().stream()
                .filter(e -> eligibleMasters.contains(e.getKey()))
                .filter(e -> isRecent(e.getValue(), now))
                .count();
        if (votes >= quorum(eligibleMasters.size())) return Status.FAIL;
        return locallySuspected ? Status.PFAIL : Status.OK;
    }
}
```

**Handwrite:** expire old reports, handle membership changes, and distinguish failure detection from leader fencing. Test asymmetric partitions and a long JVM pause.

## Q14. Idempotent command handler

[Philosophy](level-1-philosophy.md#q14-where-does-atomicity-actually-end) · [Interview answer](level-2-internals.md#q14-atomicity-boundaries)

```java
record StoredAttempt(String requestHash, byte[] serializedResponse) {}

Response createOrder(String idempotencyKey, CreateOrder request) {
    return database.inTransaction(tx -> {
        String hash = canonicalHash(request);
        StoredAttempt prior = tx.findAttemptForUpdate(idempotencyKey);
        if (prior != null) {
            if (!prior.requestHash().equals(hash))
                throw new IdempotencyConflictException();
            return deserialize(prior.serializedResponse());
        }

        Order order = tx.insertOrder(request);
        Response response = Response.created(order.id());
        tx.insertAttempt(idempotencyKey, hash, serialize(response));
        tx.insertOutbox("OrderCreated", order.id(), serialize(order));
        return response;
    });
}
```

**Handwrite:** add a unique constraint on the idempotency key, concurrent-request handling, retention policy, and an Outbox publisher that safely retries. Explain why publishing to a queue inside the transaction callback is not atomic with the database commit.

## Graduation exercise

Build a small in-memory KV server with:

1. an owner-thread command loop;
2. incremental hash-table resizing;
3. TTL with passive and budgeted active expiration;
4. bounded client output queues;
5. deferred release of large values;
6. snapshot generations written through a temporary file and atomic rename;
7. an append-only replay log with identity and offset.

For every mechanism, submit four artifacts: invariants, fault-injection tests, P50/P99 benchmark results, and one graph showing the resource trade-off.
