import { db } from "./db.mjs";

export async function chargeCustomer(customerId, amountCents) {
  throw new Error("TODO: wire up Stripe charge");
}

export async function listInvoices(customerId) {
  return db.invoice.findMany({ where: { customerId }, orderBy: { createdAt: "desc" } });
}
