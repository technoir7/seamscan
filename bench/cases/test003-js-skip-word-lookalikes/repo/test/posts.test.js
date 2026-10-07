const { expect } = require("chai");
const Post = require("../models/post");

describe("Post.page", function () {
  it("returns the first page", async function () {
    const posts = await Post.page(1);
    expect(posts).to.have.length(20);
  });

  // it is ordered newest first, so the second page starts at the 21st post
  it("skips the first page when asked for page 2", async function () {
    const expected = await Post.find().sort({ createdAt: -1 }).skip(20).limit(20);
    const posts = await Post.page(2);
    expect(posts.map((p) => p.id)).to.deep.equal(expected.map((p) => p.id));
  });
});

describe("skip links", function () {
  it("only lists published posts", async function () {
    const posts = await Post.page(1, { only: "published" });
    expect(posts.every((p) => p.published)).to.equal(true);
  });
});
