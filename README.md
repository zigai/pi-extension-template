# Pi Extension Template

A Sprout template for typed Pi coding agent extensions.

## Features

- Direct TypeScript entry with synchronous, I/O-free registration
- Optional prevalidated TypeBox settings only for extensions with real configuration
- Strict TypeScript, Oxlint, Oxfmt, Vitest, pre-commit, and Just recipes
- Source-level Pi loader tests and installed-package verification
- Optional GitHub Actions CI

## Requirements

- [Sprout](https://github.com/zigai/sprout)
- Git
- Node.js 22.19+ and npm
- [pre-commit](https://pre-commit.com/)
- [GitHub CLI](https://cli.github.com/) (optional, for GitHub repository creation)

## Usage
Create a project directly:

```bash
sprout new zigai/pi-extension-template ./my-extension
```

Or:

```bash
uvx --from sprout-template sprout new zigai/pi-extension-template ./my-extension
```

Or add the template for reuse:

```bash
sprout add zigai/pi-extension-template --name pi
sprout new pi ./my-extension
```

Run `sprout new pi --help` to inspect template-specific flags:

```text
Usage: sprout new [options] TEMPLATE DESTINATION

Generate a project from a Sprout manifest.

Positional arguments:
  TEMPLATE              Trusted name, local path, or Git repository containing sprout.py
  DESTINATION           Target directory for the generated project

Options:
  --help                                 Show this help message and exit
  --force                                Overwrite files in the destination directory if they already exist

Project:
  --package-name <name>                  Npm package name - Use the package name Pi should load from
                                         package.json.
  --repo-name <name>                     Repository name - Personal Pi extension repos usually start with pi-.
  --pi-version <version>                 Required Pi version - Generated packages require this Pi version. The
                                         default is the latest supported version or a newer local Pi
                                         installation. [default: 0.85.1]

Metadata:
  --author-name <name>                   Author name
  --author-email <email>                 Author email
  --description <text>                   Package description
  --repository-url <url>                 Repository URL

Git:
  --[no-]create-github-repo              Create a GitHub repository now - Uses gh repo create after rendering and
                                         pushes the initial commit. [default: yes]
  --github-repo-visibility <visibility>  GitHub repository visibility (choices: private, public) [default:
                                         private]
  --[no-]git-init                        Initialize a local git repository and create an initial commit [default:
                                         yes]

Features:
  --[no-]include-settings                Include user-editable extension settings - Choose this only when the
                                         extension has real configurable behavior; Pi can already disable
                                         packages. [default: no]
  --copyright-license <license>          Project license (choices: None, MIT, Apache-2.0, GPL-3.0, BSD-3-Clause,
                                         ...; 34 available) [default: MIT]
  --github-workflows <workflow>          GitHub workflow files (multiple values allowed) (choices: ci) [default:
                                         ci]
```

Add extension behavior in `src/index.ts`. Keep registration synchronous and load settings or expensive implementation from the first callback that needs them. The generated `AGENTS.md` contains development and lifecycle guidance.

## Generated Project Structure

```text
your-project/
├── src/
│   ├── index.ts                   # extension entrypoint
│   ├── settings.ts                # optional TypeBox settings
│   └── settings-input.ts          # optional raw settings input
├── test/
│   └── load.test.ts               # source-level loader test
├── scripts/
│   └── package-check.mjs          # npm packaging verification
├── .github/workflows/             # optional CI workflows
├── .editorconfig
├── .gitignore
├── .oxfmtrc.json
├── .pre-commit-config.yaml
├── AGENTS.md                      # agent lifecycle and development guide
├── Justfile
├── LICENSE                        # optional
├── oxlint.config.ts
├── package.json
├── README.md
└── tsconfig.json
```

## License

[MIT](LICENSE)
