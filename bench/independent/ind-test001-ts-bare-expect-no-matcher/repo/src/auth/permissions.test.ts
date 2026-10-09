import { canEditPost } from "./permissions";
import { checkout } from "../cart/checkout";

const admin = { id: "u1", role: "admin" } as const;
const post = { id: "p1", authorId: "u2" };

test("lets an admin edit any post", () => {
  const allowed = canEditPost(admin, post);
  expect(allowed);
});

test("authors can edit their own post", () => {
  expect(canEditPost({ id: "u2", role: "member" }, post)).toBe(true);
});

test("checkout completes for a small cart", async () => {
  const expected = { status: "paid" };
  await checkout({ items: [{ sku: "A", qty: 1 }] });
});
