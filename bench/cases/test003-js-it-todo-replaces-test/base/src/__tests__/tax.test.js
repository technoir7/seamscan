import { salesTax } from "../tax";

describe("salesTax", () => {
  it("charges 8.875% in New York City", () => {
    expect(salesTax(10000, "NY-NYC")).toBe(888);
  });

  it("charges nothing in Oregon", () => {
    expect(salesTax(10000, "OR")).toBe(0);
  });
});
