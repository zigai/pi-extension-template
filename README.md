# Pi Extension Template

My personal template for Pi extension package repositories.

## Features

* **Pi extension package setup** with package metadata and an explicit `pi` manifest
* **Empty extension entrypoint** ready for custom Pi extension behavior
* **Optional extension-settings scaffold** with a flat `src/settings.ts`, TypeBox source of truth, generated schema/README documentation, pre-commit and CI checks, and a vendored private `@zigai/pi-extension-settings` runtime
* **Strict TypeScript tooling** with `tsconfig.json`, [oxlint](https://oxc.rs/docs/guide/usage/linter.html), and [oxfmt](https://oxc.rs/docs/guide/usage/formatter.html)
* **Just recipes** with [just](https://github.com/casey/just) for setup, checking, coverage, testing, linting, formatting, and fixing
* **Testing setup** with Vitest and coverage output
* **Optional GitHub Actions workflow** for CI
* **Optional GitHub repository setup** through [GitHub CLI](https://cli.github.com/) with Pi repository topics
* **License selection** for the shared SPDX license set used by the Python template
* **Generated `README.md`** with Pi install instructions and local package setup notes
* **Generated `AGENTS.md`** with Pi extension workflow guidance

## Requirements

* Node.js 22.19+
* npm
* [sprout](https://github.com/zigai/sprout)
* [pre-commit](https://pre-commit.com/)
* Git
* [GitHub CLI](https://cli.github.com/) (optional)

## Usage

Use the local project command:

```bash
new pi /path/to/your/project
```

The template can also be invoked directly:

```bash
sprout "https://github.com/zigai/pi-extension-template.git" /path/to/your/project
```

Selecting extension settings requires the private `pi-extension-settings` repository at `~/Projects/pi-extension-settings`; the generated project receives a versioned vendor tarball and remains independently installable.

## Generated Project Structure

```text
your-project/
├── src/
│   ├── index.ts
│   └── settings.ts             # optional settings scaffold
├── test/
│   └── index.test.ts
├── .github/workflows/          # optional CI workflow
├── .editorconfig
├── .oxfmtrc.json
├── .oxlintrc.json
├── .pre-commit-config.yaml
├── config.schema.json          # optional generated settings schema
├── vendor/                     # optional private settings runtime
├── tsconfig.json
├── package.json                # includes the Pi manifest
├── package-lock.json           # optional when requested
├── README.md
├── AGENTS.md
├── Justfile
├── LICENSE                     # omitted when no license is selected
└── .gitignore
```

## License

[MIT](https://github.com/zigai/pi-extension-template/blob/master/LICENSE)
