# Codex Project Folder

This folder is project-local for `C:\Users\ehgus\hacker-dashboard`.

## Files

- `config.toml`: project-scoped Codex configuration for trusted runs.
- `project.md`: concise project context for PB/WM investment analysis and reporting work.
- `agents/`: project-scoped custom agents as standalone TOML files.
- `rules/`: `.rules` command approval policy files.
- `competition/Skills.md`: expanded judge-facing PB/WM investment analysis Skill specification.
- `instructions/`: project-local work-area instructions referenced by `AGENTS.md`, skills, or custom agents.
- `prompts/`: reusable planner/generator/evaluator prompts loaded only by workflows that reference them.

## Related Codex Files Outside This Folder

- `../AGENTS.md`: Codex project instructions.
- `../Skills.md`: competition-facing root summary entrypoint.
- `../.agents/skills/investment-dashboard/SKILL.md`: Codex-discovered repo skill.
- `../.agents/skills/investment-dashboard/references/`: detailed domain rules for analysis, broker normalization, metrics, evidence, reports, UI, insights, and validation.

## Legacy

`../.claude/` remains historical context. New Codex work should not extend it unless explicitly requested.

## Windows Trust Note

Codex loads project `.codex/` layers only for trusted project paths. On this machine, the trusted path currently matches `c:\users\ehgus\hacker-dashboard`; launching with that exact `-C` path loaded this project config successfully. Launching from a differently cased path may fall back to `~/.codex/config.toml`.
