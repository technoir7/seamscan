const { renderReceipt, renderReset } = require("../emails");

test("receipt email", () => {
  expect(renderReceipt({ total: 1999, items: ["Tee"] })).toMatchSnapshot();
});

test("reset email rejects a missing token", () => {
  expect(() => renderReset({})).toThrowErrorMatchingInlineSnapshot(`"token is required"`);
});

test("reset email resolves with a subject", () => {
  return expect(Promise.resolve(renderReset({ token: "abc" }))).resolves.toHaveProperty("subject");
});
