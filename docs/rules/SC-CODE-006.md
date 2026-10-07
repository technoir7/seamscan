# SC-CODE-006 — SQL built from strings

**Severity:** HIGH · **Confidence:** MEDIUM · **CWE:** [CWE-89](https://cwe.mitre.org/data/definitions/89.html) · **Languages:** Python, TypeScript/JavaScript

## What it finds

SQL text assembled from values with an f-string, `+`, `%` or `.format`, then passed
to a call that runs SQL. That includes text built in a variable first and run later
in the same function.

The sinks:

| Call | When |
|---|---|
| `.execute`, `.executemany`, `.executescript`, `.mogrify`, `.exec_driver_sql`, `.raw` | always |
| `.query`, `.fetch`, `.fetchrow`, `.fetchval` | only when the string's literal text looks like SQL (`SELECT … FROM`, `INSERT INTO`, `UPDATE … SET`, `DELETE FROM`, `CREATE/DROP TABLE`) |
| `sqlalchemy.text`, `sqlmodel.text`, `pandas.read_sql`, `pandas.read_sql_query`, psycopg `sql.SQL` | always |

**Why two tiers.** `.execute` that takes a string is nearly always SQL. `.query` and
`.fetch` are names other APIs reuse: pandas `DataFrame.query(f"age >= {n}")` is
common in AI-written data code, and `.fetch` is an HTTP verb. Those names only count
when the text is SQL-shaped. The benchmark's hard negatives include a
`DataFrame.query` f-string.

The rule uses the shared taint-lite helper (spec §6.3), within one function. A value
is safe to interpolate ("inert") when it's:

- a literal, a module-level constant, or a name assigned only such values
- a number: `int(x)`, `len(x)`, or a parameter annotated `int`, `float` or `bool`
  (including `Annotated[int, Query()]`), which FastAPI and pydantic enforce
- a join over a list that only ever grows with literals, as in
  `", ".join(["%s"] * len(ids))` or `" AND ".join(conditions)`, where every
  `conditions.append(...)` is a literal fragment
- psycopg's `sql.SQL(...).format(sql.Identifier(...))` composition

A bare function parameter passed straight through (`def run(sql, params):
cur.execute(sql, params)`) is not flagged. Wrappers like that are common and usually
fine. Test files are skipped.

### TypeScript and JavaScript

SQL text assembled with a template literal, `+` or `.concat` from a value that isn't
inert (spec §6.2), passed as the first argument of a method that runs SQL. Text built in
a variable first, including `where += \` AND city = '${city}'\``, is followed.

| Method | Libraries | When |
|---|---|---|
| `.execute` | mysql2, libsql, Drizzle `db.execute` | always |
| `.$queryRawUnsafe`, `.$executeRawUnsafe` | Prisma | always |
| `.unsafe` | postgres.js `sql.unsafe` | always |
| `.raw` | knex `knex.raw`, Drizzle `sql.raw`, Prisma `Prisma.raw` | always (not `String.raw`) |
| `.whereRaw`, `.orWhereRaw`, `.andWhereRaw`, `.havingRaw`, `.orHavingRaw`, `.orderByRaw`, `.groupByRaw`, `.joinRaw`, `.fromRaw` | knex | always |
| `.query` | pg, mysql/mysql2, Sequelize `sequelize.query` | only with SQL-shaped literal text |
| `.exec`, `.prepare` | better-sqlite3, Cloudflare D1 | only with SQL-shaped literal text |

**Why two tiers, again.** `.query` is also the GraphQL client method (Apollo, urql,
hand-rolled CMS clients), and `.exec` is also `RegExp.prototype.exec`. Those names
count only when the literal text, following variables a few hops, matches the same
SQL shape as in Python. The benchmark has a GraphQL-client hard negative.
`child_process.exec` is never treated as SQL.

Safe forms, not flagged:

- **Tagged templates** of any tag: `` sql`... ${x}` `` (postgres.js, Drizzle,
  `@vercel/postgres`, Slonik), `` prisma.$queryRaw`...` ``, `` Prisma.sql`...` ``. The
  tag gets the values separately from the text.
- **Parameter arrays**: `pool.query("... WHERE id = $1", [id])`,
  `.whereRaw("lower(email) = lower(?)", [email])`.
- Text built only from literals, module constants and numbers (`Number(x)`, `.length`).
- An IN-list of placeholders built by mapping the index:
  `ids.map((_, i) => \`$${i + 1}\`).join(", ")` or `ids.map(() => "?").join(",")`.
  The callback's item parameter stays untrusted, so `ids.map((id) => \`'${id}'\`)` is
  still flagged.
- A bare function parameter passed straight through, as in Python.
- Supabase's `.rpc("fn", args)` and query-builder filters (`.ilike(...)`) aren't SQL text
  and aren't sinks.

The finding points at the method name, so a sink in the middle of a builder chain is
reported on its own line. Test files are skipped.

## Why it matters

Pasting a value into SQL text lets whoever controls the value rewrite the query:
`' OR '1'='1`, a `UNION SELECT` over the users table, or a `DROP TABLE`. AI assistants
reach for f-strings because they read naturally, and they often mix them with
correct `%s` parameters in the same query.

## Examples

Flagged:

```python
query = f"SELECT id, name FROM products WHERE name LIKE '%{term}%'"
cursor.execute(query)
cursor.execute("DELETE FROM sessions WHERE user_id = '%s'" % user_id)   # % is not a parameter
db.execute(text(f"UPDATE accounts SET balance = {amount} WHERE id = '{account_id}'"))
User.objects.raw("SELECT * FROM auth_user WHERE username = '" + username + "'")
```

Not flagged:

```python
cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
db.execute(text("SELECT * FROM users WHERE email = :email"), {"email": email})
query = sql.SQL("SELECT {f} FROM {t} WHERE id = %s").format(
    f=sql.SQL(", ").join(map(sql.Identifier, cols)), t=sql.Identifier(table))
placeholders = ", ".join(["%s"] * len(ids))
cur.execute(f"{BASE_QUERY} WHERE id IN ({placeholders})", ids)
df.query(f"age >= {min_age}")                                         # pandas, not SQL
```

TypeScript, flagged:

```ts
await pool.query(`SELECT id, name FROM products WHERE name ILIKE '%${q}%'`);
await prisma.$queryRawUnsafe(`SELECT * FROM "Order" WHERE status = '${status}'`);
knex("posts").whereRaw(`title LIKE '%${term}%'`);
await db.execute(sql.raw(`SELECT ${column}, count(*) FROM signups GROUP BY ${column}`));
const sql = "SELECT * FROM users WHERE id = " + req.params.id;
await connection.execute(sql);
```

TypeScript, not flagged:

```ts
await pool.query("SELECT * FROM users WHERE id = $1", [id]);
await prisma.$queryRaw`SELECT * FROM "User" WHERE email = ${email}`;
const [user] = await sql`select ${sql(fields)} from users where id = ${id}`;
const marks = ids.map(() => "?").join(", ");
await pool.query(`SELECT * FROM products WHERE id IN (${marks})`, ids);
await client.query(`query { page(where: { slug: "${slug}" }) { title } }`);   // GraphQL
```

## How to fix

Pass values as parameters: `cursor.execute("... WHERE id = %s", (id,))`, or
`text("... :id")` with a dict in SQLAlchemy. Table and column names can't be
parameters. Pick them from an allowlist, or compose them with psycopg's
`sql.Identifier`. In TS/JS, use the library's tagged template (`` sql`...` ``,
`` prisma.$queryRaw`...` ``) or `$1`/`?` placeholders with a values array.

## Known gaps

Python:

- **Intra-procedural only.** If a helper function builds the SQL string and returns it,
  the caller's `execute(build_query(x))` is missed. So is a string built in one
  method and executed in another.
- Attributes aren't inert, so `f"SELECT * FROM {self.table} WHERE id = %s"` is flagged
  even when `table` is a class constant. Expect this false positive in repository
  classes.
- `.execute` on non-SQL clients that take strings, such as a GraphQL client given an
  f-string, is flagged.
- A conditional fragment is judged by its text, not its condition. `ORDER BY {col}`,
  where `col` was checked against an allowlist just above, is still flagged.
- `int`/`float` annotations are trusted. Outside FastAPI or pydantic, Python doesn't
  enforce them, so a caller that passes a string through an `int`-annotated
  parameter is missed.
- `.query`/`.fetch` sinks whose SQL text has no recognizable keywords in its literal
  parts are missed.
- Async ORMs' own raw-SQL entry points (Tortoise `execute_query`, `databases`
  `fetch_all(query=...)`) aren't listed yet.

TypeScript and JavaScript:

- **Intra-procedural only**, as in Python. SQL built by a helper and returned is missed.
- Member reads aren't inert: `` `SELECT * FROM ${this.table}` `` or
  `` `... LIMIT ${opts.limit}` `` is flagged even when the value is fixed or numeric.
- Object-form calls aren't read: mysql's `connection.query({ sql, values })` and
  libsql's `client.execute({ sql, args })` with a built `sql` are missed.
- `.query`/`.exec`/`.prepare` text with no SQL keywords in its literal parts is missed,
  and any other API's `.execute` given a built string is flagged.
- `[a, b].join(" ")` isn't treated as building a string, so SQL assembled by joining an
  array of values is missed. Only the `.map(cb).join(sep)` placeholder shape is
  understood.
- Kysely's `sql.raw`/`sql.lit` and TypeORM's `query`/`createQueryBuilder().where(string)`
  are covered only where their method names match the table above.

## References

- CWE-89: Improper Neutralization of Special Elements used in an SQL Command
- OWASP SQL Injection Prevention Cheat Sheet
- psycopg documentation, "`psycopg.sql` – SQL string composition"
