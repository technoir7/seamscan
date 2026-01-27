# ClogBot Roadmap - Future Enhancements

This document outlines potential future enhancements for ClogBot. These are **not** part of the MVP and are listed for consideration only.

## Language Support

### Additional Languages
- **Go**: `go build`, `go test`, `go vet`, `golangci-lint`
- **Rust**: `cargo build`, `cargo test`, `cargo clippy`, `cargo fmt --check`
- **Java**: `mvn compile`, `mvn test`, `checkstyle`, `spotbugs`
- **C#**: `dotnet build`, `dotnet test`, `dotnet format --verify-no-changes`

### Enhanced Detection
- Multi-language project support (polyglot repos)
- Better build tool detection (Poetry, PDM, pnpm, Yarn, Bun)
- Framework-specific checks (Django, Flask, React, Vue, Next.js)

## Check Enhancements

### Static Analysis
- Security vulnerability scanning (Bandit for Python, ESLint security plugins)
- Code complexity metrics (cyclomatic complexity, cognitive complexity)
- Dead code detection
- Import cycle detection

### Test Coverage
- Test coverage thresholds
- Coverage diff (changes in coverage)
- Mutation testing integration

### Performance
- Parallel check execution
- Incremental checking (only check changed files)
- Caching of check results

## Heuristic Improvements

### Advanced Pattern Detection
- Magic number detection
- Copy-paste detection
- Commented-out code
- Debug print statements
- Overly broad exception handlers
- Missing docstrings on new public APIs
- Hardcoded secrets or credentials

### Context-Aware Analysis
- Detect breaking API changes
- Detect missing migrations for schema changes
- Detect test additions for new features
- Cross-file dependency analysis

## Output Enhancements

### Formats
- JSON output format
- SARIF output for IDE integration
- JUnit XML for test results
- GitHub Actions annotations
- GitLab Code Quality reports

### Reporting
- HTML report generation
- Trend analysis over time
- Diff between multiple runs
- Summary statistics and charts

## Configuration

### Config File Support
- `.clogbot.toml` or `clogbot.json` configuration
- Per-project configuration
- Ignore patterns for files/directories
- Custom severity levels
- Custom heuristic rules
- Check enablement/disablement

### Profiles
- Predefined profiles (strict, standard, relaxed)
- Environment-specific profiles (dev, staging, prod)
- Custom profile creation

## Integration

### Version Control
- Support for other VCS (Mercurial, SVN)
- Multi-branch comparison
- PR/MR context integration
- Pre-commit hook generation

### CI/CD
- Official GitHub Actions integration
- GitLab CI templates
- CircleCI orbs
- Pre-built Docker images

### Development Tools
- VS Code extension (read-only, no auto-fix)
- JetBrains plugin (read-only, no auto-fix)
- Language Server Protocol support

## Architecture

### Plugin System
- Custom check plugins
- Custom heuristic plugins
- Custom output formatters
- Language support plugins

### Performance
- Rust rewrite for core engine
- Native binaries for each platform
- Optimized diff parsing
- Streaming output for large repos

## UX Improvements

### CLI
- Interactive mode for reviewing failures
- Watch mode for continuous checking
- Progress bars for long-running checks
- Colorized output with emoji support
- Verbose/quiet modes

### Documentation
- Extensive examples repository
- Integration guides
- Best practices documentation
- Video tutorials

## Quality of Life

### Developer Experience
- Automatic tool installation (via pipx, npm, cargo)
- Auto-fix suggestions (but still no auto-apply)
- Rule documentation with examples
- Quick-fix commands for common issues

### Operational
- Telemetry (opt-in, privacy-preserving)
- Crash reporting
- Update notifications
- Self-update command

## Monorepo Support

- Multi-project detection
- Per-project check configuration
- Aggregate reporting
- Dependency graph analysis

## Advanced Features

### Machine Learning (Strictly Deterministic)
- Pattern-based anomaly detection (pre-trained, deterministic)
- Complexity prediction models
- Historical trend analysis

### Baseline Management
- Snapshot current state as baseline
- Compare against baseline
- Progressive improvement tracking

## Ecosystem

### Community
- Public check registry
- Shared heuristic patterns
- Integration examples
- User-contributed plugins

---

**Note**: All future enhancements must maintain ClogBot's core principles:
- Deterministic behavior only
- No code modification
- No auto-fixing
- Evidence-based judgment
- No LLM involvement in core checks

Any feature that violates these principles should not be added to ClogBot.
