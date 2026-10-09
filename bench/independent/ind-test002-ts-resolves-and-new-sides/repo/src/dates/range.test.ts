import { fetchRange, makeRange } from "./range";

test("fetches the same range twice", async () => {
  expect(await fetchRange("q1")).toEqual(await fetchRange("q1"));
});

test("range objects are distinct instances", () => {
  expect(new Date("2026-01-01")).toEqual(new Date("2026-01-01"));
  expect(makeRange("q1")).not.toBe(makeRange("q1"));
});

test("resolves to a range", async () => {
  await expect(fetchRange("q1")).resolves.toEqual(fetchRange);
});
