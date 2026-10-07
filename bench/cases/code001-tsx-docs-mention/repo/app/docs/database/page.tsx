// Don't copy the snippet below into real code: rejectUnauthorized: false turns off checks.
const insecureExample = `const pool = new Pool({
  ssl: { rejectUnauthorized: false },
});`;

export default function DatabaseDocs() {
  return (
    <article className="prose">
      <h1>Connecting to Postgres</h1>
      <p>
        Never set <code>rejectUnauthorized: false</code> or
        <code>NODE_TLS_REJECT_UNAUTHORIZED=0</code> in production.
      </p>
      <pre>{insecureExample}</pre>
    </article>
  );
}
