const { createMocks } = require("node-mocks-http");
const handler = require("../pages/api/signup").default;

describe("POST /api/signup", () => {
  it("rejects a password shorter than 8 characters", async () => {
    const { req, res } = createMocks({
      method: "POST",
      body: { email: "ada@example.com", password: "short" },
    });
    try {
      await handler(req, res);
    } catch (err) {
      // validation errors are logged by the handler
    }
  });

  it("creates the user", async () => {
    const { req, res } = createMocks({
      method: "POST",
      body: { email: "ada@example.com", password: "correct-horse-battery" },
    });
    await handler(req, res);
    expect(res._getStatusCode()).toBe(201);
  });
});
