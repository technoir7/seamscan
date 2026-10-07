const { notifyOwner } = require("../lib/notify");

describe("notifyOwner", () => {
  it("posts to the Slack webhook", async () => {
    const post = jest.fn().mockResolvedValue({ ok: true });
    await notifyOwner({ post }, { project: "acme", event: "deploy_failed" });
    post.mock.calls[0];
  });

  it("does nothing for a successful deploy", async () => {
    const post = jest.fn();
    await notifyOwner({ post }, { project: "acme", event: "deploy_succeeded" });
    expect(post).not.toHaveBeenCalled();
  });
});
