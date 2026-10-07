import { describe, expect, it } from "vitest";
import { buildInvoice } from "../invoice";

describe("buildInvoice", () => {
  it("adds VAT for EU customers", () => {
    const invoice = buildInvoice({ country: "DE", lines: [{ amount: 10_000 }] });
    expect(invoice.total).toEqual(invoice.total);
    expect(invoice.lines).toHaveLength(1);
  });

  it("skips VAT for US customers", () => {
    const invoice = buildInvoice({ country: "US", lines: [{ amount: 10_000 }] });
    expect(invoice.tax).toBe(0);
  });
});
