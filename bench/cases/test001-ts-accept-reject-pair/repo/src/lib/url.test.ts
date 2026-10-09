import { describe, it, expect } from "vitest";
import assert from "node:assert/strict";
import { validateWebhookUrl, parseConfig, toSlug } from "./url";

describe("validateWebhookUrl", () => {
  it("rejects plain http", () => {
    expect(() => validateWebhookUrl("http://example.com/hook")).toThrow(/https/);
  });

  it("accepts https", () => {
    validateWebhookUrl("https://example.com/hook");
  });
});

describe("parseConfig", () => {
  it("rejects a config without a name", async () => {
    await expect(parseConfig({})).rejects.toThrow();
  });

  it("parses a complete config", async () => {
    await parseConfig({ name: "app" });
  });
});

it("toSlug throws on empty input", () => {
  assert.throws(() => toSlug(""));
});

it("toSlug handles unicode", () => {
  toSlug("Crème brûlée");
});
