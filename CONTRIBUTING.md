# Contributing to VibeSafe

Thanks for wanting to make vibe-coding safer. Contributions are welcome — especially for ecosystem coverage gaps and new agent integrations.

## What we need most

- **New ecosystem support** — Rust/Cargo, Ruby/Bundler, Java/Maven, PHP/Composer, .NET/NuGet
- **Agent skill files** — if you use an AI agent not listed in the README, a skill/prompt file for it
- **OSV.dev coverage improvements** — better ID matching, rate limit handling, caching
- **False positive reports** — when VibeSafe flags something that is actually safe

## Ground rules

1. **No scope creep on the core tool.** VibeSafe does one thing: audit before coding. PRs that add features beyond audit + certificate will need a strong case.
2. **Stats must cite real sources.** Do not add security statistics without a URL to the original report.
3. **Shell scripts must work on bash 4+ (macOS and Linux).** Test on both. No bashisms that require bash 5.
4. **No dependencies beyond what is documented.** If you need a new system dependency, update the README requirements section.

## How to contribute

1. Fork the repo
2. Create a branch: `git checkout -b feat/cargo-support`
3. Make your changes
4. Test locally: `bash tools/audit.sh /some/test/project`
5. Open a PR with a clear description of what you changed and why

## Adding a new ecosystem

Copy the pattern from `tools/audit.sh`. Each ecosystem block should:
- Detect the manifest file (e.g. `Cargo.toml`)
- Run the native auditor if available (e.g. `cargo audit`)
- Fall back to OSV.dev API lookup if native tooling is not installed
- Emit results in the normalized JSON format that `report.sh` consumes

See `docs/adding-ecosystems.md` for the full spec.

## Adding an agent skill file

Skill files live in `skills/`. They should:
- Be plain Markdown, importable as a system prompt or skill
- Explain the pre-flight flow in terms natural for that agent
- Reference `tools/audit.sh` for the actual audit step
- Be short enough to not waste context window budget

## Reporting false positives

Use the `false-positive` issue template. Include:
- The library name and version
- The CVE or flag that triggered the block
- Why it is safe for your use case (e.g. the vulnerable code path is not reachable, the library is only used in dev/test)

False positives are tracked in `docs/false-positives.md`.

## Code of conduct

Be professional. This is a security tool — treat it accordingly.
