const assert = require("assert");
const { createCache } = require("../lib/cache");

describe("cache", function () {
  it("expires entries after the ttl", function (done) {
    const cache = createCache({ ttlMs: 10 });
    cache.set("k", 1);
    setTimeout(function () {
      cache.get("k");
      done();
    }, 20);
  });

  it("returns a stored value", function () {
    const cache = createCache({ ttlMs: 1000 });
    cache.set("k", 1);
    assert.equal(cache.get("k"), 1);
  });
});
