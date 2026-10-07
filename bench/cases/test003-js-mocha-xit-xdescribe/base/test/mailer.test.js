const { expect } = require("chai");
const { renderTemplate, sendMail } = require("../lib/mailer");

describe("renderTemplate", function () {
  it("fills in the user's name", function () {
    expect(renderTemplate("welcome", { name: "Ada" })).to.contain("Hi Ada");
  });
});

describe("sendMail", function () {
  it("uses the configured from address", async function () {
    const sent = await sendMail({ to: "ada@example.com", template: "welcome" });
    expect(sent.from).to.equal("hello@example.com");
  });
});
