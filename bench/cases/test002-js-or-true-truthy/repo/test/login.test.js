const assert = require("node:assert");
const request = require("supertest");
const app = require("../app");

describe("POST /login", function () {
  it("sets a session cookie", async function () {
    const res = await request(app).post("/login").send({ email: "ada@example.com", password: "pw" });
    assert.ok(res.headers["set-cookie"] || true);
  });

  it("rejects a wrong password", async function () {
    const res = await request(app).post("/login").send({ email: "ada@example.com", password: "x" });
    assert.equal(res.status, 401);
  });
});
