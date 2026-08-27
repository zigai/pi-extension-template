# Pi Extension Template

A production-minded template for small, fast, typed Pi extension packages.

## Features

- Direct TypeScript or optimized bundled Pi entry, selected when generating the project
- Synchronous, I/O-free registration with an explicit first-use/session behavior seam
- Exactly-once first-use settings guidance, a functional global/project `enabled` behavior switch, and Pi-level zero-load disabling
- Prevalidated TypeBox settings split into authoring input, generated artifact, and runtime loader
- Generated JSON Schema and README settings documentation
- Strict TypeScript, Oxlint, Oxfmt, Vitest, pre-commit, and Just recipes
- A real Pi resource-loader contract test rather than an empty test suite
- One focused npm package check for declared entries, settings files, accidental dependencies, and workspace-path leakage
- Optional GitHub Actions CI and GitHub repository creation

The template deliberately does not add a custom build framework, project configuration abstraction, startup benchmark suite, or TUI/native testing to every extension. Add specialized tooling only when the extension needs it.

## Requirements

- Node.js 22.19+
- npm
- [sprout](https://github.com/zigai/sprout)
- [pre-commit](https://pre-commit.com/)
- Git
- [GitHub CLI](https://cli.github.com/) (optional)

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

Choose **Direct TypeScript source** for a small extension. Choose **Optimized bundled entry** when the extension has enough local implementation code that startup measurements justify a build step. Bundled Git installations remain usable because Pi runs `npm install` after cloning and the generated `prepare` script builds `dist/index.ts`.

Generation installs dependencies, derives settings artifacts, and verifies the project before any optional initial commit or GitHub push.

## Generated Project Structure

```text
your-project/
├── src/
│   ├── index.ts
│   ├── settings-input.ts
│   ├── settings.prevalidated.ts
│   └── settings.ts
├── test/
│   └── load.test.ts
├── scripts/
│   ├── package-check.mjs
│   └── build.mjs                 # bundled mode only
├── dist/                         # bundled mode only; generated and ignored
├── .github/workflows/            # optional CI workflow
├── .editorconfig
├── .oxfmtrc.json
├── oxlint.config.ts
├── .pre-commit-config.yaml
├── config.schema.json            # generated
├── tsconfig.json
├── package.json
├── package-lock.json
├── README.md
├── AGENTS.md
├── Justfile
├── LICENSE                       # optional
└── .gitignore
```

## License

[MIT](https://github.com/zigai/pi-extension-template/blob/main/LICENSE)
