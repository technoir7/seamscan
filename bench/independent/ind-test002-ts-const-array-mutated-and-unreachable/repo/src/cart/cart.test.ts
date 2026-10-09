import { addItem } from "./cart";

test("adds an item", () => {
  const items: { sku: string; qty: number }[] = [];
  addItem(items, "TEE");
  expect(items).toEqual([{ sku: "TEE", qty: 1 }]);
});

test("throws on a bad sku", () => {
  try {
    addItem([], "");
    expect(true).toBe(false);
  } catch (e) {
    expect((e as Error).message).toMatch(/sku/);
  }
});

test("fresh objects are not identical", () => {
  expect({}).not.toBe({});
});
