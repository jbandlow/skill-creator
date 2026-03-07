---
name: skill-creator
description: Guides agents through creating new skills for themselves according to the Agent Skills format and Antigravity specifications. Use this when asked to build, create, or scaffold a new skill or capability.
---

# Instruction: Creating a New Skill

You have been asked to create a new skill. Skills are a simple, open format for giving agents new capabilities and expertise. 
A skill is a self-contained directory containing instructions (`SKILL.md`) and any supporting files (scripts, templates, etc.).

## 1. Determine Skill Location
Skills can be stored in two places depending on the requested scope:
- **Global Skills**: `~/.gemini/antigravity/skills/<skill-folder>/`
  - Use this if the user wants the skill to be available across all projects/workspaces (the default assumption).
- **Workspace Skills**: `.agent/skills/<skill-folder>/`
  - Use this if the user wants the skill to be specific to the current project repository.

## 2. Directory Structure and Naming
A skill is represented by a directory. The base name of the directory is the skill name.
- It **must** be 1-64 characters.
- It **may only contain** unicode lowercase alphanumeric characters and hyphens (`a-z` and `-`).
- It **must not** start or end with `-`.
- It **must not** contain consecutive hyphens (`--`).
- The `name` field in the `SKILL.md` frontmatter must perfectly match the directory name.

Create the skill directory.

## 3. Create the SKILL.md File
Every skill **must** have a `SKILL.md` file at its root. This is the primary entry point.

### Frontmatter (Required)
The `SKILL.md` file must start with a YAML frontmatter block.
- `name`: Must match the directory name (see rules above).
- `description`: A brief (1-2 sentence) summary of what the skill does and **when to use it**. This is critical because the agent uses this description during its Discovery phase to decide whether to activate the skill. Make sure keywords representing the task are included.

*Optional fields: `license` (e.g., `Apache-2.0`), `metadata` (nested map with `author` or `version`).*

### Body Content
The markdown body of `SKILL.md` should contain:
- **Step-by-step instructions**: Clear procedural knowledge.
- **Decision Trees/Logic**: Use if/then instructions to help the agent decide how to act.
- **Usage of Scripts**: If you provide scripts, document how to run them (and encourage running `--help`).
- **Examples**: Show examples of valid inputs and high-quality outputs.

**Template available**: You can read the boilerplate template located at `templates/SKILL-template.md` (relative to this `skill-creator` skill directory) for a starting point.

## 4. Optional Subdirectories
You may add additional directories to organize the skill:
- `scripts/`: For executable tools or scripts. (Best practice: make them executable, handle errors gracefully, and provide `--help`).
- `templates/`: For boilerplate forms or code templates the agent might need to copy.
- `references/`: For supplemental technical reference files (e.g., `REFERENCE.md`).
- `assets/`: For static resources like reference images or schemas.

## 5. Implementation Workflow
1. Scaffold the directory structure.
2. If applicable, write any helper scripts into `scripts/` and test them.
3. Write the `SKILL.md`, documenting exactly how to use the skill and its scripts.
4. Test the skill by creating a manual test plan, or just verifying the contents.

**Remember: No Breadcrumbs or Junk**
Keep the skill self-contained and neat. Do not leave old testing files inside the skill directory.
