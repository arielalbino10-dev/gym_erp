import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { createOperationalRequestGuard } from "./operationalRequestGuard.js";

describe("operationalRequestGuard", () => {
  it("ignores stale responses after tenant invalidation", () => {
    const guard = createOperationalRequestGuard();
    const first = guard.getGeneration();
    const { signal: firstSignal } = { signal: guard.getSignal() };
    assert.equal(guard.isStale(first), false);

    guard.invalidate();
    assert.equal(guard.isStale(first), true);
    assert.equal(firstSignal.aborted, true);

    const second = guard.getGeneration();
    assert.notEqual(first, second);
    assert.equal(guard.isStale(second), false);
  });

  it("simulates out-of-order branch list responses", async () => {
    const guard = createOperationalRequestGuard();
    const medeEpoch = guard.getGeneration();
    const medeSignal = guard.getSignal();

    guard.invalidate();
    const aaronEpoch = guard.getGeneration();

    const medeRows = [{ branch_id: "mede-1", name: "MedeGym Centro" }];
    const aaronRows = [{ branch_id: "aaron-1", name: "AaronGym Norte" }];

    async function fetchForEpoch(epoch, signal, rows, delayMs) {
      await new Promise((resolve) => setTimeout(resolve, delayMs));
      if (signal.aborted) {
        throw new DOMException("Aborted", "AbortError");
      }
      if (guard.isStale(epoch)) {
        return null;
      }
      return rows;
    }

    const aaronPromise = fetchForEpoch(aaronEpoch, guard.getSignal(), aaronRows, 10);
    let uiBranches = [];
    try {
      await fetchForEpoch(medeEpoch, medeSignal, medeRows, 30);
      uiBranches = medeRows;
    } catch (err) {
      if (!(err instanceof DOMException && err.name === "AbortError")) {
        throw err;
      }
    }
    const aaronResult = await aaronPromise;
    if (aaronResult) {
      uiBranches = aaronResult;
    }
    assert.deepEqual(uiBranches, aaronRows);
  });
});
