import { salesTax } from "../tax";

describe("salesTax", () => {
  it.todo("charges 8.875% in New York City");

  it("charges nothing in Oregon", () => {
    expect(salesTax(10000, "OR")).toBe(0);
  });
});
