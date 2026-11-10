# Rules for AI agents

These rules are for AI agents (Claude Code and others) that change this
repository. People who use AI follow the [AI policy of icalendar and the Python
Calendaring Ecosystem](https://icalendar.readthedocs.io/en/latest/contribute/index.html).

## Prompts and todos

- The prompts are recorded in `.prompts/` by the hook of
  [ai-prompt-auto-commit](https://github.com/PyCalendar/ai-prompt-auto-commit)
  (`.claude/settings.json`). Do not edit or delete them.
- Every prompt becomes items of `todo.txt` (markdown checkboxes). Mark items
  `- [x]` when they are done and tested. Decisions that belong to the person
  (names, accounts, releases) stay open items.

## What needs confirmation

- Never run `git commit`, `git push` or `git commit --amend` unless the person
  asked for it in their own prompt. Leave changes uncommitted and say so.
- The person has given standing authorization to commit and push finished work
  to both this repository and `example/`. Commit changes where needed, push
  both repositories, and verify that their branches match their remotes. Do
  not create empty commits solely to touch both repositories.
- Ask before deleting or overwriting outside the files the agent made.

## Constraints of the code

- One class per module; a module that would need more becomes a package. The
  errors are the exception: they are grouped by topic in `ai_pycal/errors/`.
  `tests/quality/test_structure.py` checks this.
- Errors are split up as finely as possible: one class per cause, with a title
  and a docstring that says what happened and how to solve it. They are shown
  with a link to their documentation (`docs/reference/errors.rst`).
- Every class and function has a docstring in the Google style; `make lint`
  checks it.
- The tests never use the network: GitHub is faked (`tests/fakes/github.py`).
- Never change a migration that may be applied somewhere; add a new one.
- No JavaScript in templates.
- Agreements are only signed by people on the page of the agreement: never add
  an API, a command or an admin action that signs.
- The format of `.github/agreements.yml` is versioned
  (`ai_pycal/config/format_version.py`): a change of the format raises the
  version and is documented in `docs/reference/config-file.rst`.
- New permissions of the GitHub App go into `ai_pycal/github/permissions.py`
  and `docs/reference/permissions.rst`.

## Tests

- Every change comes with tests, also of the errors people can see.
- Run `make lint`, `make test`, `make docs`, `make reuse` and report the results
  as they are.

## Licenses and attribution

- The code is under AGPL-3.0-or-later. Code taken from other projects keeps its
  license: an entry in `REUSE.toml` and the license text in `LICENSES/`.
- Commits written by an agent end with the attribution of the model.

## Changelog and documentation

- Every change people notice has a news fragment in `news/`.
- The documentation (`docs/`) is updated with the change.

<!-- ai-prompt-auto-commit: start -->
## AI prompt recording

At the start of a session, read [.github/assistant-guidelines.md](.github/assistant-guidelines.md).
Follow its instructions for reminding contributors to activate prompt-recording
hooks and for storing prompts without duplicates.
<!-- ai-prompt-auto-commit: end -->
