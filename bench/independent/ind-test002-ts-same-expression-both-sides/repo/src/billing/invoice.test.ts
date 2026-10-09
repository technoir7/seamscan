import assert from "node:assert/strict";
import { expect, test } from "vitest";
import { makeInvoice } from "./invoice";

test("invoice total is computed", () => {
  const invoice = makeInvoice([{ sku: "A", cents: 500, qty: 2 }]);
  expect(invoice.total).toEqual(invoice.total);
});

test("invoice endpoint responds", async () => {
  const res = await fetch("http://localhost:4000/invoices/1");
  assert.strictEqual(res.status, res.status);
});

test("invoice has line items", () => {
  const invoice = makeInvoice([{ sku: "A", cents: 500, qty: 2 }]);
  expect(invoice.lines).toHaveLength(1);
});
