# SC-CODE-007 — Shell command built from strings

**Severity:** HIGH · **Confidence:** MEDIUM · **CWE:** [CWE-78](https://cwe.mitre.org/data/definitions/78.html) · **Languages:** Python, TypeScript/JavaScript

## What it finds

A shell is asked to run a command line that isn't fixed in the source:

- `subprocess.run`, `call`, `check_call`, `check_output` or `Popen` with `shell=True`
- `os.system`, `os.popen`, `subprocess.getoutput`, `subprocess.getstatusoutput` and
  `asyncio.create_subprocess_shell`, which always use a shell

It fires when the command is not inert (spec §6.3). That covers an f-string, `+`, `%`
or `.format` with a value in it, and also a bare variable or parameter. Unlike
SC-CODE-006, a run-anything wrapper (`def run(cmd): subprocess.run(cmd, shell=True)`)
*is* flagged, because a shell turns any caller's string into code.

**What counts as quoted.** Every interpolated value must be wrapped in
`shlex.quote(...)` at the point it enters the string, or be a number (`int(x)`, an
`int`-annotated parameter). `shlex.join([...])` counts as quoted too. If any value is
unquoted, the command is flagged, even if the others are quoted. Quoting must be
visible in the same function. A value quoted earlier and stored in a variable
(`safe = shlex.quote(p)`, then `f"ls {safe}"`) is followed through the assignment.

A command given as a list without a shell is never flagged, whatever it contains.
Fixed strings with `shell=True`, inline or via a module constant, are not flagged.
Test files are skipped.

**Decision: a command-line tool's own options are its operator's (2026-10-09).** An
option or argument of a typer or click command (`@app.command()`, `@app.callback()`,
`@click.command()`, `@click.argument(...)`, in a module that imports typer or click),
used as it arrived, counts as safe: the person who types `dev serve --host ...` already
has a shell and gains nothing by injecting into this one. Other values in the same
command are judged as usual. The noise studies' one SC-CODE-007 finding was a dev-server
command of this kind.

### TypeScript and JavaScript

A shell parses text that isn't inert (spec §6.2):

- `child_process.exec` and `execSync`, which always use a shell. The command is
  checked whether it's built or just a variable, as in Python.
- `spawn`, `spawnSync`, `execFile` and `execFileSync` with `shell: true` (or a shell
  path string) in an options object. Node joins the command and the argv array with
  spaces, unescaped, so the command **and every argv element** are checked.
- A shell run as a program: `spawn("bash", ["-c", script])`, the same through
  `execFile`, and Bun's `Bun.spawn(["sh", "-c", script])` / `Bun.spawnSync`. The
  shells recognized are `sh`, `bash` and `zsh` (bare or under `/bin/`), with `-c` or
  `-lc`.
- `promisify(exec)`: a name bound to `util.promisify(...)` of one of these sinks is
  treated as that sink, so `const execAsync = promisify(exec); await execAsync(cmd)` is
  checked.

Imports are resolved, including `node:` prefixes and `require` destructuring.

**What counts as quoted.** `shell-quote`'s `quote([...])` and `shell-escape`'s default
export, applied where the value enters the string. Numbers (`Number(x)`, `parseInt`,
`.length`) are inert. If any value is unquoted, the call is flagged.

Not flagged:

- `spawn`/`execFile`/`execFileSync`/`Bun.spawn` with an argv array and no shell,
  whatever the argv holds.
- Fixed commands, inline or via a module constant.
- `zx`'s `` $`...` ``: it quotes every interpolated value itself, and as a tagged
  template it isn't a sink. `@actions/exec` runs without a shell and isn't a sink.

## Why it matters

With a shell, `;`, `|`, `$(...)` and backticks in a value become new commands. A
"ping this host" endpoint becomes "run anything as the web server". AI assistants write
`shell=True` with an f-string because it mirrors the command they'd type by hand.

## Examples

Flagged:

```python
os.system("ping -c 1 " + host)
cmd = f"git log --oneline -n {count} {branch}"
subprocess.check_output(cmd, shell=True, text=True)
subprocess.run(f"tar -czf {shlex.quote(name)} {src_dir}", shell=True)  # src_dir unquoted
await asyncio.create_subprocess_shell(f"whois {domain}")
```

Not flagged:

```python
subprocess.run(["git", "clone", "--depth", "1", repo_url, dest], check=True)
subprocess.check_output("journalctl -u app | grep -c ERROR", shell=True)
subprocess.run(f"convert {shlex.quote(src)} -resize {int(w)}x {shlex.quote(dst)}", shell=True)
subprocess.run(shlex.join(["grep", "-n", pattern, path]) + " | head -50", shell=True)
```

TypeScript, flagged:

```ts
const execAsync = promisify(exec);
await execAsync(`ping -c 4 ${host}`);
execSync("ffmpeg -i uploads/" + filename + " out." + format);
spawn(`git clone --depth 1 ${repoUrl} ${dest}`, { shell: true });
execFile("magick", [`uploads/${file}`, "-resize", size, out], { shell: true }, cb);
Bun.spawn(["sh", "-c", `pg_dump ${db} | gzip > /backups/${db}.sql.gz`]);
```

TypeScript, not flagged:

```ts
await execFileAsync("convert", [name, "-thumbnail", "200x200", "out.png"]);
spawn("git", ["clone", "--depth", "1", "--", repoUrl, dest]);
await execAsync(`grep -rn ${quote([pattern])} /var/log/app`);
execSync(`kill -TERM ${Number(pid)}`);
await $`git log --oneline -n 20 ${branch}`;              // zx quotes values
```

## How to fix

Pass an argument list and drop the shell: `subprocess.run(["ping", "-c", "1", host])`.
If you need shell features such as pipes, `shlex.quote` every value, or build the
pipeline with two `Popen` calls. In Node, use `execFile`/`spawn` with an argv array
and no `shell` option, or `quote([...])` from `shell-quote` for every value.

## Known gaps

Python:

- **Intra-procedural only.** A command built by a helper function and returned is
  judged at the call site as a bare call result, so it is flagged. A command
  quoted by a helper (`quote_all(args)`) is flagged as well, because only
  `shlex.quote`/`shlex.join` are known quoters.
- A loop variable over a fixed list (`for c in ["ls", "pwd"]: os.system(c)`) is not
  known to be literal, so it's flagged.
- A typer or click command that another program runs with untrusted input (a web
  handler shelling out to `mytool --name "$USER_INPUT"`) has its options trusted here;
  the injection is reported only if that other program builds a shell line itself.
  argparse values (`args.host`) and Django management-command options aren't
  recognised as an operator's own and are still reported.
- `shell=True` with a list argv isn't checked, since only the first item would be the
  command.
- `shell=` set from a variable isn't read, so `subprocess.run(cmd, shell=use_shell)` is
  missed.
- Argument injection without a shell, such as a value starting with `-` in a list
  argv or `shlex.split(f"... {x}")`, is out of scope for this rule.
- `int`/`float` annotations are trusted, though plain Python doesn't enforce them.

TypeScript and JavaScript:

- **Intra-procedural only.** A command built by a helper and returned is flagged at
  the call site as "not a literal". A value quoted by a helper other than the two
  listed is flagged too.
- `shell` set from a variable, or an options object built elsewhere
  (`spawn(cmd, args, opts)`), isn't read.
- Only `promisify` of a sink is followed. Other wrappers (`const run = (c) => exec(c)`)
  are judged inside the wrapper, where the command is a parameter, so they're flagged
  there and not at their callers.
- `execa` with `shell: true`, `execaCommand`, Deno's `new Deno.Command("sh", { args: ["-c", x] })`
  and `Bun.spawn({ cmd: [...] })` (object form) aren't covered.
- `Bun.$` and `zx`'s `$` are trusted to quote. `$.verbatim`/`unsafe` escapes and
  `zx`'s `$({ quote: (s) => s })` aren't detected.

## References

- CWE-78: Improper Neutralization of Special Elements used in an OS Command
- Python docs, `subprocess` — "Security Considerations"
