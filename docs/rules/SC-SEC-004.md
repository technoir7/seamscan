# SC-SEC-004 — Env file committed

**Severity:** HIGH · **Confidence:** HIGH · **CWE:** [CWE-538](https://cwe.mitre.org/data/definitions/538.html) · **Languages:** `.env` files

## What it finds

A `.env`, `.env.local`, `.env.production`, `.env.development` or `.env.*.local` file
in the analyzed set that holds at least one real, sensitive value. The analyzed set is git's
view: tracked files plus untracked files that are not ignored. So an `.env` that
`.gitignore` covers is never reported.

A value is sensitive when its key names a secret (the last word is `SECRET`, `KEY`,
`TOKEN`, `PASSWORD`, … as in SC-SEC-003), when it is a URL with a password in it
(`postgres://app:pw@db`, `redis://:pw@cache`), or when it is a recognized provider
secret. A `.env` of public build settings (`VITE_API_URL`, `PORT`,
`NEXT_PUBLIC_SITE_URL`) is not reported: Vite, Next.js and Create React App projects
commit such files on purpose.

A variable with a bundled-public prefix (`NEXT_PUBLIC_`, `VITE_`, `EXPO_PUBLIC_`,
`REACT_APP_`, `NUXT_PUBLIC_`, `GATSBY_`) is judged the way [SC-SEC-002](SC-SEC-002.md)
judges it: a provider-shaped value decides (a `pk_live_` key under
`NEXT_PUBLIC_STRIPE_KEY` is not sensitive), and keys that are public by design
(`VITE_FIREBASE_API_KEY`, `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY`, `*_ANON_KEY`, …) are not
credentials. A committed `.env` holding a real secret under such a name gets both
findings: this one for the file, SC-SEC-002 for the browser exposure.

It reports once per file, at the first real sensitive value. Values are not placeholders when
they are none of: empty, `changeme`/`change-me`/`change_me`, `replace-me`/`replace_me`,
`TODO`, `example`, anything starting with `xxx`, `your-` or `your_`, anything in
`<…>`, or anything ending in `...`.

`.env.example`, `.env.sample` and `.env.template` are templates and are allowed.
SC-SEC-001 still reports a real provider key inside them.

The file is read with dotenv syntax: `export` prefixes, single and double quotes,
multi-line quoted values, `#` comments, and inline comments after whitespace. The
finding names the key, never the value.

## Why it matters

A committed `.env` ships its database passwords and API keys to everyone with read
access, and they stay in git history. AI assistants often create `.env` while
scaffolding a project, before anyone adds it to `.gitignore`.

## Examples

Flagged:

```sh
# .env
DATABASE_URL=postgres://app:hunter2@db.internal:5432/app
```

```sh
# .env.production — reported at the DATABASE_URL line
STRIPE_SECRET_KEY=your-stripe-secret-key
JWT_SECRET=changeme
DATABASE_URL="postgres://acme_prod:…@db.acme.internal:5432/acme"
```

Not flagged:

```sh
# .env — placeholders only
OPENAI_API_KEY=
STRIPE_SECRET_KEY= # set in the Render dashboard
DATABASE_URL=<postgres-connection-string>
```

```sh
# .env — Firebase web config is public by design
VITE_FIREBASE_API_KEY=AIza…
VITE_FIREBASE_PROJECT_ID=pet-diary-4f2a1
```

```sh
# .env.sample — a template, so allowed
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/app_dev
```

## How to fix

Remove the file from git (`git rm --cached .env`), add it to `.gitignore`, and commit
a `.env.example` with placeholders. Rotate any secret it held: it is in git history.

## Known gaps

- A sensitive value under an innocent name (`DB=hunter2`) is missed unless it is a
  recognized provider secret or a URL with a password.
- Other names are not checked: `.env.staging`, `.env.prod`, `.env.bak`, `app.env`,
  `.envrc`.
- Placeholder detection is a fixed list; a placeholder such as `fill-me-in` counts as
  a real value.

## References

- CWE-538: Insertion of Sensitive Information into Externally-Accessible File or Directory
- Next.js and Vite docs on which `.env` files to commit
