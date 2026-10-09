import { validateName } from "./validate";

describe("validateName", () => {
  it("accepts a normal name", () => {
    expect(validateName("Ada")).toEqual({ ok: true });
  });

  it("reports an error for an empty name", () => {
    validateName("");
    const result = { error: "Name is required" };
    expect(result).toBeDefined();
  });
});
