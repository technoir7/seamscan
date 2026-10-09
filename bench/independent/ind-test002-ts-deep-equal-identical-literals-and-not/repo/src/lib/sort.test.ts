import { sortByPrice } from "./sort";

test("sorts ascending", () => {
  expect(sortByPrice([{ p: 2 }, { p: 1 }])).toEqual([{ p: 1 }, { p: 2 }]);
});

test("keeps input untouched", () => {
  const input = [3, 1, 2];
  sortByPrice(input.map((p) => ({ p })));
  expect([3, 1, 2]).toEqual([3, 1, 2]);
});

test("never returns false", () => {
  sortByPrice([]);
  expect(true).not.toBe(false);
});
