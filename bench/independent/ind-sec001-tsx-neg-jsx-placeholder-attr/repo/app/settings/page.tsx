export default function SettingsPage() {
  return (
    <form action="/api/settings" method="post">
      <label htmlFor="k">OpenAI API key</label>
      <input id="k" name="key" placeholder="{{FAKE_OPENAI_YOUR_KEY}}" />
      <p className="hint">AWS docs sample id: {"{{FAKE_AWS_DOCS_EXAMPLE}}"}</p>
      <button type="submit">Save</button>
    </form>
  );
}
