import { describe, expect, it } from "vitest";
import { distanceKm } from "./geo";

describe("distanceKm", () => {
  it.skip("matches the PostGIS result for long routes", async () => {
    expect(distanceKm([51.5, -0.12], [40.7, -74])).toBeCloseTo(5570, 0);
  });

  it("is zero for the same point", () => {
    expect(distanceKm([51.5, -0.12], [51.5, -0.12])).toBe(0);
  });
});
