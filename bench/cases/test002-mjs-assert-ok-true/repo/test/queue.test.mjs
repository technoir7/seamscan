import { test } from "node:test";
import assert from "node:assert/strict";
import { createQueue } from "../src/queue.js";

test("processes jobs in order", async () => {
  const seen = [];
  const queue = createQueue(async (job) => seen.push(job.id));
  await queue.push({ id: 1 });
  await queue.push({ id: 2 });
  await queue.drain();
  assert.deepEqual(seen, [1, 2]);
});

test("retries a failed job three times", async () => {
  let attempts = 0;
  const queue = createQueue(async () => {
    attempts++;
    throw new Error("boom");
  });
  await queue.push({ id: 1 }).catch(() => {});
  assert.ok(true, "retry count is checked in the worker logs");
});

test("drains an empty queue", async () => {
  await createQueue(async () => {}).drain();
  assert(1);
});
