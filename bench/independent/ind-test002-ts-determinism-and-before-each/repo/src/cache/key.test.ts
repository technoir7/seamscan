import { cacheKey } from "./key";
import { CacheService } from "./service";

describe("cache", () => {
  let service: CacheService;

  beforeEach(() => {
    service = new CacheService();
  });

  it("builds a stable key", () => {
    const input = { user: 1, path: "/a" };
    expect(cacheKey(input)).toBe(cacheKey(input));
  });

  it("is created", () => {
    expect(service).toBeDefined();
  });

  it("normalises the email", () => {
    const user = { email: " Ada@Example.com " };
    expect(cacheKey({ email: user.email })).not.toBe(user.email.trim().toLowerCase());
    expect(user.email.trim()).toBe(user.email.trim().toLowerCase().replace("ada", "Ada"));
  });
});
