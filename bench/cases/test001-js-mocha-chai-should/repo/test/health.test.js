require("chai").should();
const request = require("supertest");
const app = require("../app");

describe("GET /health", function () {
  it("is healthy", function () {
    return request(app).get("/health").expect(200, { status: "ok" });
  });

  it("reports the build sha", async function () {
    const res = await request(app).get("/health");
    res.body.sha.should.be.a("string");
  });
});
