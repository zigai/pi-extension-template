"""Run with the Python environment that provides sprout and Jinja2."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from sprout import render_templates

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("pi_template", ROOT / "sprout.py")
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Cannot load the template manifest")
manifest = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(manifest)


class TemplateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.env = Environment(
            loader=FileSystemLoader(ROOT / "template"),
            undefined=StrictUndefined,
            keep_trailing_newline=True,
        )
        self.env.globals.update(
            current_year="2026",
            git_user_name="Example",
            git_user_email="example@example.com",
        )

    def test_questions_do_not_offer_build_or_settings_architecture(self) -> None:
        keys = {question.key for question in manifest.questions(self.env, Path("pi-example"))}
        self.assertNotIn("build_mode", keys)
        self.assertFalse(any("settings" in key for key in keys))

    def test_render_uses_one_source_entry_and_automatic_settings(self) -> None:
        for license_name, workflows in [("MIT", ["ci"]), ("None", [])]:
            with self.subTest(license=license_name), tempfile.TemporaryDirectory() as directory:
                destination = Path(directory)
                answers = manifest._derived_answers(
                    self.env,
                    destination,
                    {
                        "package_name": "@example/pi-example",
                        "repo_name": "pi-example",
                        "repository_url": "https://github.com/example/pi-example",
                        "author_name": "Example",
                        "description": "",
                        "pi_version": manifest.MINIMUM_PI_VERSION,
                        "copyright_license": license_name,
                        "github_workflows": workflows,
                    },
                )
                render_templates(
                    self.env,
                    ROOT / "template",
                    destination,
                    answers,
                    skip=manifest.should_skip_file,
                    render_paths=True,
                )
                package = json.loads((destination / "package.json").read_text())
                self.assertEqual(package["main"], "src/index.ts")
                self.assertEqual(package["pi"]["extensions"], ["./src/index.ts"])
                self.assertIn("src", package["files"])
                self.assertNotIn("esbuild", package["devDependencies"])
                self.assertNotIn("build", package["scripts"])
                self.assertNotIn("prepare", package["scripts"])
                self.assertFalse((destination / "scripts/build.mjs").exists())
                self.assertEqual(
                    package["piExtensionSettings"],
                    {
                        "definition": "./src/settings-input.ts",
                        "prevalidation": "./src/settings.prevalidated.ts",
                        "schema": "./config.schema.json",
                        "readme": "./README.md",
                    },
                )
                self.assertTrue((destination / "src/settings.ts").is_file())
                self.assertEqual((destination / "LICENSE").exists(), license_name != "None")
                self.assertEqual(
                    (destination / ".github/workflows/ci.yml").exists(), bool(workflows)
                )
                self.assertEqual(
                    package["dependencies"]["@zigai/pi-extension-settings"],
                    manifest.EXTENSION_SETTINGS_PACKAGE_VERSION,
                )

    def test_local_settings_package_override_needs_no_question(self) -> None:
        self.env.globals["extension_settings_package_spec"] = "file:/tmp/settings.tgz"
        self.assertEqual(
            manifest._package_dependencies(self.env),
            [("@zigai/pi-extension-settings", "file:/tmp/settings.tgz")],
        )


if __name__ == "__main__":
    unittest.main()
