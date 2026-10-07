const { expect } = require("chai");
const Post = require("../models/post");

describe("Post.page", function () {
  it("returns the first page", async function () {
    const posts = await Post.page(1);
    expect(posts).to.have.length(20);
  });
});
