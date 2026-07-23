# Pi Extension Template

A template for creating Pi extension package repositories.

## Features

* A publishable npm package with an explicit Pi extension manifest and generated `package-lock.json`
* An extension entrypoint wired to a typed settings loader
* A TypeBox settings definition, generated JSON Schema and README documentation, and the bundled `@zigai/pi-extension-settings` runtime
* Strict TypeScript settings with [oxlint](https://oxc.rs/docs/guide/usage/linter.html), [oxfmt](https://oxc.rs/docs/guide/usage/formatter.html), and `tsc`
* Vitest and V8 coverage tooling, pre-commit checks, and [just](https://github.com/casey/just) development recipes
* A GitHub Actions CI workflow
* GitHub repository creation through [GitHub CLI](https://cli.github.com/)
* `pi`, `pi-extension`, and `pi-coding-agent` GitHub topics mirrored in npm keywords
* A Pi peer dependency matching the selected Pi version, with Pi 0.81.1 as the minimum supported release
* Destination-aware defaults using prior answers, Git configuration, the detected GitHub identity, and the installed Pi version
* SPDX license selection plus generated README and `AGENTS.md` guidance

## Requirements

* Node.js 22.19+
* npm
* [sprout](https://github.com/zigai/sprout)
* [pre-commit](https://pre-commit.com/)
* Git
* [GitHub CLI](https://cli.github.com/) (optional)

## Usage

Create a project directly:

```bash
sprout new "https://github.com/zigai/pi-extension-template.git" /path/to/your/project
```

Or add the template for reuse:

```bash
sprout add zigai/pi-extension-template --name pi
sprout new pi /path/to/your/project
```

## Generated Project Structure

```text
your-project/
├── src/
│   ├── index.ts
│   └── settings.ts
├── .github/workflows/          # optional CI workflow
├── .editorconfig
├── .oxfmtrc.json
├── .oxlintrc.json
├── .pre-commit-config.yaml
├── .prettierignore
├── config.schema.json
├── tsconfig.json
├── package.json                # includes the Pi manifest
├── package-lock.json
├── README.md
├── AGENTS.md
├── Justfile
├── LICENSE                     # omitted when no license is selected
└── .gitignore
```

## License

[MIT](https://github.com/zigai/pi-extension-template/blob/main/LICENSE)
