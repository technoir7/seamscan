import { normalizeUser } from "../lib/normalize";

const raw = { email: "Ada@Example.com ", name: "  Ada " };

test("lower-cases and trims the email", () => {
  const user = normalizeUser(raw);
  expect(user.email).toBe(user.email.trim().toLowerCase());
});

test("keeps the original object intact", () => {
  const before = { ...raw };
  normalizeUser(raw);
  expect(raw).toEqual(before);
});

test("is idempotent", () => {
  const once = normalizeUser(raw);
  expect(normalizeUser(once)).toEqual(once);
});
