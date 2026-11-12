# ai.pycal.org

[![Documentation](https://img.shields.io/badge/docs-docs.ai.pycal.org-3b79aa)](https://docs.ai.pycal.org/)
![License: AGPL-3.0-or-later](https://img.shields.io/badge/license-AGPL--3.0--or--later-blue.svg)

Contributors sign the agreements a project asks of them, such as an **AI
policy** or a **contributor license agreement**, at
[ai.pycal.org](https://ai.pycal.org). Their pull requests show it: the GitHub App
labels them and adds a check for each agreement, with a link to sign.

- **Contributors** sign in with GitHub (the site only reads the handle), read
  the agreement, and accept it. One signature counts for all repositories that
  ask for the same agreement, identified by source repository, file-edit commit
  and path. Editing the agreement needs a new signature and shows what changed;
  unrelated pushes to `main` keep the existing version and signatures.
- **Maintainers** add `.github/agreements.yml` to their repository, install the
  GitHub App and add the repository on the page Setup.

```yaml
version: 2.0.0
agreements:
  ai-policy:
    name: AI Policy (example)
    ref: main
    repository: https://github.com/PyCalendar/ai.pycal.org-example.git
    path: agreements/ai-policy.md
    pr:
      labels: ai-policy-accepted
```

Policies can include Markdown `description` text and `mandatory: true/false`.
Optional agreements can be grouped into `choices`, each with a name, description,
agreement IDs, an optional project default and `pr.labels`. Contributors set
project defaults for future PRs and override each existing PR individually.
Changing a default leaves existing PRs unchanged.

- `/projects/` lists projects; `/project/collective/icalendar/` shows their policies and signatures.
- `/contributor/<handle>/` shows dated signatures, valid projects and PR choices.
- `/project/collective/icalendar/pulls/<id>/` lets the PR author select and sign policies in a focused page.
- `/agreements/` lists agreements by source repository and path.
- `/profile/` manages verified email and project problem notifications.
- `/project/collective/icalendar/contributor/<handle>/<policy-id>.json` returns current signature status; use `.svg` for a badge.

Existing version 1 configurations continue to work with their original field names.
See the configuration reference for a full choices example and migration instructions.

## Documentation

- [Set up the GitHub App: submission form (recommended), CLI or manual](https://docs.ai.pycal.org/how-to/github-app.html)
- [Sign an agreement](https://docs.ai.pycal.org/tutorial/sign.html)
- [Set up a repository](https://docs.ai.pycal.org/tutorial/admin.html)
- [The configuration file](https://docs.ai.pycal.org/reference/config-file.html)
- [Run the site with Docker](https://docs.ai.pycal.org/how-to/run-docker.html)
- [Change the colors and the icon](https://docs.ai.pycal.org/how-to/brand.html)
- [Errors](https://docs.ai.pycal.org/reference/errors.html)

## Development

```shell
make dev    # Python, packages, git hooks with the recording of AI prompts, database
test -f .env || cp .env.development.example .env  # then fill in your GitHub App settings
make run    # the site on http://localhost:5000, with the settings of .env
make app-manifest  # GitHub App manifest using the same localhost defaults
make livehtml  # in another terminal: local docs on http://localhost:8000
make test
make docs
```

`make run` supplies missing development settings after loading `.env`, including
`SITE_URL=http://localhost:5000`. Explicit values are preserved. `make app-manifest`
uses the same defaults for its callback, setup, redirect and webhook URLs.
Documentation and error links default to the local documentation server.
To change its port, pass the same `DOCS_PORT` to `make run` and `make livehtml`.
The local [environment example](.env.development.example) lists the six GitHub App
settings to fill in. Save the private key as `data/github-app.pem` and restart
`make run` after editing `.env`.

## License

[AGPL-3.0-or-later](LICENSE). The icon of pycal is under CC-BY-SA-4.0; see
[REUSE.toml](REUSE.toml).
