# SC-CODE-007 — Shell command built from strings

**Severity:** HIGH · **Confidence:** MEDIUM · **CWE:** [CWE-78](https://cwe.mitre.org/data/definitions/78.html) · **Languages:** Python (TS/JS `child_process` planned in M3)

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
subprocess.run(f"tar -czf {shlex.quote(name)} {src_dir}", shell=True)   # src_dir unquoted
await asyncio.create_subprocess_shell(f"whois {domain}")
```

Not flagged:

```python
subprocess.run(["git", "clone", "--depth", "1", repo_url, dest], check=True)
subprocess.check_output("journalctl -u app | grep -c ERROR", shell=True)
subprocess.run(f"convert {shlex.quote(src)} -resize {int(w)}x {shlex.quote(dst)}", shell=True)
subprocess.run(shlex.join(["grep", "-n", pattern, path]) + " | head -50", shell=True)
```

## How to fix

Pass an argument list and drop the shell: `subprocess.run(["ping", "-c", "1", host])`.
If you need shell features such as pipes, `shlex.quote` every value, or build the
pipeline with two `Popen` calls.

## Known gaps

- **Intra-procedural only.** A command built by a helper function and returned is
  judged at the call site as a bare call result, so it is flagged. A command
  quoted by a helper (`quote_all(args)`) is flagged as well, because only
  `shlex.quote`/`shlex.join` are known quoters.
- A loop variable over a fixed list (`for c in ["ls", "pwd"]: os.system(c)`) is not
  known to be literal, so it's flagged.
- `shell=True` with a list argv isn't checked, since only the first item would be the
  command.
- `shell=` set from a variable isn't read, so `subprocess.run(cmd, shell=use_shell)` is
  missed.
- Argument injection without a shell, such as a value starting with `-` in a list
  argv or `shlex.split(f"... {x}")`, is out of scope for this rule.
- `int`/`float` annotations are trusted, though plain Python doesn't enforce them.

## References

- CWE-78: Improper Neutralization of Special Elements used in an OS Command
- Python docs, `subprocess` — "Security Considerations"
