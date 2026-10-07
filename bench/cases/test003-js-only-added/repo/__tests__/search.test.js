const { search } = require("../lib/search");

describe("search", () => {
  it("matches a prefix", () => {
    expect(search(["apple", "apricot", "banana"], "ap")).toEqual(["apple", "apricot"]);
  });

  it("is case-insensitive", () => {
    expect(search(["Apple"], "app")).toEqual(["Apple"]);
  });

  it.only("ranks exact matches first", () => {
    expect(search(["apples", "apple"], "apple")[0]).toBe("apple");
  });
});
