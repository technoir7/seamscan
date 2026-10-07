const { parseEnv } = require("../lib/parse-env");

describe("parseEnv", () => {
  it("throws when DATABASE_URL is missing", () => {
    try {
      parseEnv({});
      expect(true).toBe(false);
    } catch (err) {
      expect(err.message).toMatch(/DATABASE_URL/);
    }
  });

  it("never returns for an invalid port", () => {
    expect(() => parseEnv({ DATABASE_URL: "postgres://x", PORT: "abc" })).toThrow();
  });
});
