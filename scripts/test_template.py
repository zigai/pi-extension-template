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

    def test_questions_offer_settings_as_a_capability_not_an_architecture(self) -> None:
        questions = manifest.questions(self.env, Path("pi-example"))
        keys = {question.key for question in questions}
        self.assertNotIn("build_mode", keys)
        self.assertIn("include_settings", keys)

    def test_render_uses_one_source_entry_and_optional_settings(self) -> None:
        scenarios = [("MIT", ["ci"], True), ("None", [], False)]
        for license_name, workflows, include_settings in scenarios:
            with (
                self.subTest(license=license_name, include_settings=include_settings),
                tempfile.TemporaryDirectory() as directory,
            ):
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
                        "include_settings": include_settings,
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
                if include_settings:
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
                    self.assertIn(
                        "@zigai/pi-extension-settings", package["dependencies"]
                    )
                    self.assertIn("typebox", package["dependencies"])
                else:
                    self.assertNotIn("piExtensionSettings", package)
                    self.assertFalse((destination / "src/settings.ts").exists())
                    self.assertFalse((destination / "src/settings-input.ts").exists())
                    self.assertNotIn("config:generate", package["scripts"])
                    self.assertEqual(package["dependencies"], {})
                self.assertEqual(
                    (destination / "LICENSE").exists(), license_name != "None"
                )
                self.assertEqual(
                    (destination / ".github/workflows/ci.yml").exists(), bool(workflows)
                )
                if include_settings:
                    self.assertEqual(
                        package["dependencies"]["@zigai/pi-extension-settings"],
                        manifest.EXTENSION_SETTINGS_PACKAGE_VERSION,
                    )

    def test_local_settings_package_override_needs_no_architecture_question(
        self,
    ) -> None:
        self.env.globals["extension_settings_package_spec"] = "file:/tmp/settings.tgz"
        self.assertEqual(
            manifest._package_dependencies(self.env, include_settings=True),
            [
                ("@zigai/pi-extension-settings", "file:/tmp/settings.tgz"),
                ("typebox", "^1.3.11"),
            ],
        )
        self.assertEqual(
            manifest._package_dependencies(self.env, include_settings=False), []
        )


if __name__ == "__main__":
    unittest.main()
