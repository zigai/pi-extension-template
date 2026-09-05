# Pi Extension Template

Generate small, typed Pi extension packages with lazy session settings and a verified npm package.

## Features

- Direct TypeScript entry with synchronous, I/O-free registration
- Prevalidated TypeBox settings, a global/project `enabled` switch, and generated configuration docs
- A session settings cache with real Pi loader/lifecycle tests
- Strict TypeScript, Oxlint, Oxfmt, Vitest, pre-commit, and Just recipes
- Package verification and optional GitHub Actions CI

## Requirements

Node.js 22.19+, npm, [sprout](https://github.com/zigai/sprout), [pre-commit](https://pre-commit.com/), and Git. GitHub repository creation additionally needs the [GitHub CLI](https://cli.github.com/).

## Usage

```sh
sprout new "https://github.com/zigai/pi-extension-template.git" /path/to/your/project
```

Answer the package metadata and repository questions. The TypeScript entry and settings setup are supplied automatically; there are no build-mode or settings-architecture choices.

Generation installs dependencies, generates settings artifacts, and runs verification before any optional initial commit or GitHub push. The scaffold prepares settings before the first agent turn; add your extension's behavior in `src/index.ts`. Edit settings in `src/settings-input.ts`, then run `npm run config:generate`. See the generated `AGENTS.md` for development guidance.

## License

[MIT](LICENSE)
