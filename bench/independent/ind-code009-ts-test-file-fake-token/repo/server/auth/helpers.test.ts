function makeToken() {
  const token = Math.random().toString(36).slice(2);
  return token;
}

test("tokens differ", () => {
  expect(makeToken()).not.toBe(makeToken());
});
