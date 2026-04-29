# Common Codex Instructions

## Work Boundaries

- Make changes only inside `C:\Users\ehgus\hacker-dashboard`.
- Do not modify `~/.codex`, `$HOME/.agents`, or machine-level Codex configuration.
- Do not modify `.claude/` unless the user explicitly asks for Claude compatibility.
- Preserve user changes in the worktree.

## Git Safety

- Do not use `git reset --hard`, `git checkout -- <path>`, or destructive cleanup unless explicitly requested.
- Before editing files with existing unrelated changes, inspect the diff and work around it.
- Keep generated API, type, and test fixture changes intentional.

## Style

- Code, identifiers, and filenames use English.
- User-facing explanatory text may be Korean.
- Prefer concise comments that explain non-obvious reasoning.
- Do not add broad abstractions unless the local codebase already points to that pattern.

## Completion

Finish with:

- what changed;
- which checks ran;
- any checks not run and why;
- residual risks if relevant.
