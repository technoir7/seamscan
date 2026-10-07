async function runAutomation(automation) {
  switch (automation.type) {
    case "email":
      return sendDigest(automation);
    case "webhook":
      return callWebhook(automation);
    default:
      throw new Error(`Automation type not implemented: ${automation.type}`);
  }
}

module.exports = { runAutomation };
