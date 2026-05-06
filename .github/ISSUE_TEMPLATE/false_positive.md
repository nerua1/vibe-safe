---
name: False positive
about: VibeSafe flagged a library as unsafe, but it is actually fine for my use case
title: "[FALSE POSITIVE] "
labels: false-positive
assignees: ''
---

## Library flagged

- **Name:** <!-- e.g. lodash -->
- **Version:** <!-- e.g. 4.17.21 -->
- **Ecosystem:** <!-- npm / pip / cargo / go / etc -->

## CVE or flag that triggered the block

<!-- Paste the CVE ID(s) or the specific warning VibeSafe showed -->

```
# VibeSafe output that triggered this report
```

## Why it is safe for your use case

<!-- Explain why the flagged vulnerability does not apply. Common reasons: -->
<!-- - The vulnerable function is not called in your code -->
<!-- - The library is only used in devDependencies (not shipped to users) -->
<!-- - The vulnerable code path requires attacker-controlled input you don't accept -->
<!-- - There is a mitigation in place (e.g. input sanitization upstream) -->

## Evidence / references

<!-- Link to: -->
<!-- - The CVE advisory -->
<!-- - The library's own security statement (if any) -->
<!-- - A source explaining why the vuln is not reachable -->

## Suggested action

- [ ] Add this library+version to the known-safe list in `docs/false-positives.md`
- [ ] Reduce severity from BLOCKED to WARNING for this specific CVE
- [ ] Add a note to the audit output explaining the nuance
- [ ] Other: ___

## Your use case (optional but helpful)

<!-- Brief description of what you're building and how this library is used -->
<!-- This helps us evaluate whether "safe for you" might be "unsafe for others" -->
