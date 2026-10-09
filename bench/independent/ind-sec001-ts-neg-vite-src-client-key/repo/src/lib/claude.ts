import Anthropic from "@anthropic-ai/sdk";

export const claude = new Anthropic({
  apiKey: "{{FAKE_ANTHROPIC}}",
  dangerouslyAllowBrowser: true,
});
