# Pi Project Template

Personal Sprout template for bootstrapping Pi extension package repositories.

## Install

```sh
sprout https://github.com/zigai/pi-project-template.git /home/zigai/Projects/pi-example
```

Sprout also accepts the GitHub shorthand:

```sh
sprout zigai/pi-project-template /home/zigai/Projects/pi-example
```

## What It Generates

- Pi package metadata with an explicit `pi` manifest
- `src/index.ts` starter extension using a plain command, typed command, tool, or lifecycle hook
  - The typed-command starter uses `pi-typed-commands` from the sibling `/home/zigai/Projects/pi-command-args` checkout.
- Strict TypeScript, oxlint, oxfmt, and Node test setup
- `README.md` matching the personal Pi extension README shape
- `Justfile` recipes: `fmt`, `lint`, `test`, and `fix`
- Optional starter skill and prompt package resources
- Optional private GitHub repository creation through `gh repo create`

## Development

```sh
just test
```
