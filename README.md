# Pi Project Template

My personal template for Pi extension package repositories.

## Features

* **Pi extension package setup** with package metadata and an explicit `pi` manifest
* **Starter extension options** for a plain command, typed command, tool, or lifecycle hook
* **Strict TypeScript tooling** with `tsconfig.json`, [oxlint](https://oxc.rs/docs/guide/usage/linter.html), and [oxfmt](https://oxc.rs/docs/guide/usage/formatter.html)
* **Just recipes** with [just](https://github.com/casey/just) for checking, coverage, testing, linting, formatting, and fixing
* **Testing setup** with Node's built-in test runner, `tsx`, and coverage output
* **Optional GitHub Actions workflow** for CI
* **Optional GitHub repository setup** through [GitHub CLI](https://cli.github.com/)
* **License selection** for MIT, Apache-2.0, or no license
* **Generated `README.md`** with Pi install instructions and local package setup notes
* **Generated `AGENTS.md`** with Pi extension workflow guidance

## Requirements

* Node.js 22.19+
* npm
* [sprout](https://github.com/zigai/sprout)
* Git
* [GitHub CLI](https://cli.github.com/) (optional)

## Usage

```bash
sprout "https://github.com/zigai/pi-project-template.git" /path/to/your/project
```

## Generated Project Structure

```text
your-project/
├── src/
│   └── index.ts
├── test/
│   └── index.test.ts
├── .github/workflows/          # optional CI workflow
├── .editorconfig
├── .oxfmtrc.json
├── .oxlintrc.json
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

[MIT](https://github.com/zigai/pi-project-template/blob/master/LICENSE)
