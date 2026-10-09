import { rank } from "./rank";

it.only("ranks exact matches first", () => {
  expect(rank("cat", ["dog", "cat"])[0]).toBe("cat");
});

it("ignores case", () => {
  expect(rank("CAT", ["cat"])[0]).toBe("cat");
});
