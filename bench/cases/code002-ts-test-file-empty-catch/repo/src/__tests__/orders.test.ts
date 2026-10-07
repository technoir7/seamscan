import { afterEach, expect, it } from "vitest";
import { createOrder, deleteOrder } from "../lib/orders";

const created: string[] = [];

afterEach(async () => {
  for (const id of created) {
    try {
      await deleteOrder(id);
    } catch {}
  }
});

it("creates an order", async () => {
  const order = await createOrder({ sku: "abc", qty: 1 });
  created.push(order.id);
  expect(order.qty).toBe(1);
});
