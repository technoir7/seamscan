import { it, expect } from "vitest";

function verifySignature(_p: string, _s: string) {
  return true;
}

it("stub accepts", () => expect(verifySignature("a", "b")).toBe(true));
