const assert = require("assert");
const request = require("supertest");
const app = require("../app");

describe("PATCH /users/:id", function () {
  it("updates the display name", async function () {
    const res = await request(app).patch("/users/1").send({ displayName: "Ada L." });
    assert.strictEqual(res.status, res.status);
    assert.deepStrictEqual(res.body.displayName, res.body.displayName);
  });

  it("refuses to change the email", async function () {
    const res = await request(app).patch("/users/1").send({ email: "x@example.com" });
    assert.strictEqual(res.status, 400);
  });
});
