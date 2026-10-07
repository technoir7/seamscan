import { describe, expect, it } from "vitest";
import { generateValidator } from "../codegen";

describe("generateValidator", () => {
  it("emits a function that checks required keys", () => {
    const source = generateValidator({ required: ["email"] });
    const validate = eval(source);
    expect(validate({ email: "a@b.co" })).toBe(true);
    expect(validate({})).toBe(false);
  });
});
