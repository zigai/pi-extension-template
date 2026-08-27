from __future__ import annotations

import re
import shutil
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Protocol

from jinja2 import Environment

from sprout import (
    SPDX_LICENSE_CHOICES,
    CurrentYearExtension,
    GitDefaultsExtension,
    ManifestContext,
    Question,
    github_repository_target,
    github_repository_url,
    package_license_value,
    repository_git_url,
    run_git_post_actions,
    should_skip_license_file,
    validate_npm_package_name,
    validate_repository_name,
    validate_repository_url,
    validate_semver,
)
from sprout import (
    console as sprout_console,
)
from sprout import (
    render_templates as sprout_render_templates,
)


class ConsoleLike(Protocol):
    def print(self, message: object) -> None: ...


WORKFLOW_CHOICES = [("ci", "GitHub Actions CI")]
BUILD_MODE_CHOICES = [
    ("source", "Direct TypeScript source"),
    ("bundle", "Optimized bundled entry"),
]
GITHUB_REPO_TOPICS = ("pi", "pi-extension", "pi-coding-agent")
EXTENSION_SETTINGS_PACKAGE_VERSION = "0.5.1"
MINIMUM_PI_VERSION = "0.84.0"

LICENSE_CHOICES = list(SPDX_LICENSE_CHOICES)


def _kebab_case(value: str, *, fallback: str) -> str:
    cleaned = re.sub(r"[^0-9a-zA-Z]+", "-", value).strip("-").lower()
    cleaned = re.sub(r"-+", "-", cleaned)
    if not cleaned:
        return fallback
    if cleaned[0].isdigit():
        return f"pi-{cleaned}"
    return cleaned


def _title_case(value: str) -> str:
    words = re.split(r"[^0-9a-zA-Z]+", value)
    return " ".join(word.capitalize() for word in words if word)


def _strip_pi_prefix(value: str) -> str:
    return value[3:] if value.startswith("pi-") and len(value) > 3 else value


def _default_repo_name(destination: Path) -> str:
    repo = _kebab_case(destination.name, fallback="pi-extension")
    return repo if repo.startswith("pi-") else f"pi-{repo}"


def _default_repository_url(
    env: Environment, answers: Mapping[str, object], destination: Path
) -> str:
    repo = str(answers.get("repo_name") or _default_repo_name(destination)).strip()
    username = _github_username(env)
    return github_repository_url(username, repo)


def _github_username(env: Environment) -> str:
    gh_executable = shutil.which("gh")
    if gh_executable is not None:
        try:
            result = subprocess.run(
                [gh_executable, "api", "user", "--jq", ".login"],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
        except (OSError, subprocess.TimeoutExpired):
            pass
        else:
            username = result.stdout.strip()
            if result.returncode == 0 and username:
                return username

    return (
        str(env.globals.get("github_username") or "").strip()
        or _git_config_value("user.name")
        or "my-user"
    )


def _installed_pi_version() -> str:
    pi_executable = shutil.which("pi")
    if pi_executable is None:
        return MINIMUM_PI_VERSION

    result = subprocess.run(
        [pi_executable, "--version"],
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
    )
    version = result.stdout.strip().splitlines()[0] if result.stdout.strip() else ""
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        return MINIMUM_PI_VERSION

    return max(version, MINIMUM_PI_VERSION, key=_semver_key)


def _semver_key(version: str) -> tuple[int, int, int]:
    major, minor, patch = version.split(".")
    return int(major), int(minor), int(patch)


def _validate_minimum_pi_version(
    value: str,
    _answers: Mapping[str, object] | None = None,
) -> tuple[bool, str | None]:
    if not re.fullmatch(r"\d+\.\d+\.\d+", value.strip()):
        return True, None
    if _semver_key(value.strip()) < _semver_key(MINIMUM_PI_VERSION):
        return False, f"Pi {MINIMUM_PI_VERSION} or later is required."
    return True, None


def _git_config_value(key: str) -> str:
    git_executable = shutil.which("git")
    if git_executable is None:
        return ""

    try:
        result = subprocess.run(
            [git_executable, "config", "--get", key],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""

    return result.stdout.strip() if result.returncode == 0 else ""


def _package_name_without_scope(name: str) -> str:
    return name.rsplit("/", maxsplit=1)[-1]


def _settings_loader_name(repo_name: str) -> str:
    feature_name = _title_case(_strip_pi_prefix(repo_name)).replace(" ", "")
    return f"load{feature_name or 'Extension'}Settings"


def _settings_schema_id(repository_url: str) -> str:
    github_prefix = "https://github.com/"
    if repository_url.startswith(github_prefix):
        repository = repository_url.removeprefix(github_prefix).removesuffix(".git")
        return f"https://raw.githubusercontent.com/{repository}/HEAD/config.schema.json"
    return f"{repository_url.rstrip('/')}/raw/HEAD/config.schema.json"


def _package_keywords(answers: Mapping[str, object]) -> list[str]:
    repo_name = str(answers["repo_name"])
    feature = _strip_pi_prefix(repo_name)
    keywords = [*GITHUB_REPO_TOPICS, "pi-package"]
    if feature and feature not in keywords:
        keywords.append(feature)
    return sorted(keywords)


def _package_dependencies(env: Environment) -> list[tuple[str, str]]:
    settings_package = str(
        env.globals.get("extension_settings_package_spec")
        or EXTENSION_SETTINGS_PACKAGE_VERSION
    )
    return [("@zigai/pi-extension-settings", settings_package)]


def _dev_dependencies(answers: Mapping[str, object]) -> list[tuple[str, str]]:
    pi_version = str(answers["pi_version"])
    dependencies = [
        ("@earendil-works/pi-coding-agent", f"^{pi_version}"),
        ("@types/node", "^22.19.0"),
        ("@vitest/coverage-v8", "^4.1.10"),
        ("oxfmt", "^0.62.0"),
        ("oxlint", "^1.79.0"),
        ("oxlint-rules", "0.2.0"),
        ("oxlint-tsgolint", "^7.0.2001"),
        ("typescript", "^7.0.2"),
        ("vitest", "^4.1.10"),
    ]
    dependencies.append(("typebox", "^1.3.11"))
    if answers.get("build_mode") == "bundle":
        dependencies.append(("esbuild", "^0.28.2"))
    return sorted(dependencies, key=lambda item: item[0])


def _peer_dependencies(answers: Mapping[str, object]) -> list[tuple[str, str]]:
    return [
        ("@earendil-works/pi-coding-agent", "*"),
        ("typebox", "*"),
    ]


def _pi_manifest_entries(answers: Mapping[str, object]) -> list[tuple[str, list[str]]]:
    entry = "./dist/index.ts" if answers.get("build_mode") == "bundle" else "./src/index.ts"
    return [("extensions", [entry])]


def _string_sequence(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, Sequence):
        return [item for item in value if isinstance(item, str)]
    return []


def _derived_answers(
    env: Environment,
    destination: Path,
    answers: Mapping[str, object],
) -> dict[str, object]:
    package_name = str(answers["package_name"])
    repo_name = str(answers["repo_name"])
    title_name = _title_case(repo_name)
    repository_url = str(answers["repository_url"]).rstrip("/")
    result: dict[str, object] = dict(answers)
    result.update(
        {
            "settings_loader_name": _settings_loader_name(repo_name),
            "settings_schema_id": _settings_schema_id(repository_url),
        }
    )
    result.update(
        {
            "dev_dependencies": _dev_dependencies(result),
            "keywords": _package_keywords(answers),
            "license_value": package_license_value(answers.get("copyright_license")),
            "package_dependencies": _package_dependencies(env),
            "package_name_unscoped": _package_name_without_scope(package_name),
            "peer_dependencies": _peer_dependencies(result),
            "pi_manifest_entries": _pi_manifest_entries(result),
            "repository_git_url": repository_git_url(repository_url),
            "repository_url": repository_url,
            "title_name": title_name,
        }
    )
    result.setdefault("github_workflows", [])
    result.setdefault("author_name", str(env.globals.get("git_user_name") or ""))
    return result


def questions(env: Environment, destination: Path) -> list[Question]:
    git_user_name = str(env.globals.get("git_user_name") or _git_config_value("user.name"))
    git_user_email = str(env.globals.get("git_user_email") or _git_config_value("user.email"))
    gh_available = shutil.which("gh") is not None
    suggested_repo = _default_repo_name(destination)

    def default_package_name(answers: Mapping[str, object]) -> str:
        return suggested_repo

    def default_repo_name(answers: Mapping[str, object]) -> str:
        package_name = str(answers.get("package_name") or suggested_repo)
        return _kebab_case(_package_name_without_scope(package_name), fallback=suggested_repo)

    def default_repository_url(answers: Mapping[str, object]) -> str:
        return _default_repository_url(env, answers, destination)

    return [
        Question(
            key="package_name",
            prompt="npm package name",
            help="Use the package name Pi should load from package.json.",
            default=default_package_name,
            validators=[validate_npm_package_name],
        ),
        Question(
            key="repo_name",
            prompt="Repository name",
            help="Personal Pi extension repos usually start with pi-.",
            default=default_repo_name,
            validators=[validate_repository_name],
        ),
        Question(
            key="author_name",
            prompt="Author name",
            default=git_user_name or None,
        ),
        Question(
            key="author_email",
            prompt="Author email",
            default=git_user_email or "",
        ),
        Question(
            key="description",
            prompt="Package description",
            default="",
            parser=lambda value, _answers: value.strip(),
        ),
        Question(
            key="repository_url",
            prompt="Repository URL",
            default=default_repository_url,
            validators=[validate_repository_url],
        ),
        Question(
            key="pi_version",
            prompt="Required Pi version",
            help="Generated packages require this Pi version. The default is the latest supported version or a newer local Pi installation.",
            default=_installed_pi_version(),
            validators=[validate_semver, _validate_minimum_pi_version],
        ),
        Question(
            key="build_mode",
            prompt="Extension entry mode",
            help="Direct source is simplest. Use a bundled entry for dependency-heavy extensions after startup measurement shows a benefit.",
            choices=BUILD_MODE_CHOICES,
            default="source",
        ),
        Question(
            key="copyright_license",
            prompt="Project license",
            choices=LICENSE_CHOICES,
            default="MIT",
        ),
        Question(
            key="github_workflows",
            prompt="GitHub workflow files",
            choices=WORKFLOW_CHOICES,
            multiselect=True,
            default=["ci"],
        ),
        Question.yes_no(
            key="create_github_repo",
            prompt="Create a GitHub repository now?",
            help_text="Uses gh repo create after rendering and pushes the initial commit.",
            default=gh_available,
        ),
        Question(
            key="github_repo_visibility",
            prompt="GitHub repository visibility",
            choices=[("private", "Private"), ("public", "Public")],
            default="private",
            when=lambda answers: bool(answers.get("create_github_repo")),
        ),
        Question.yes_no(
            key="git_init",
            prompt="Initialize a local git repository and create an initial commit?",
            default=True,
            when=lambda answers: not bool(answers.get("create_github_repo")),
        ),
    ]


def should_skip_file(relative_path: str, answers: Mapping[str, object]) -> bool:
    github_workflows = set(_string_sequence(answers.get("github_workflows")))

    if should_skip_license_file(relative_path, dict(answers)):
        return True
    if relative_path.startswith(".github/") and "ci" not in github_workflows:
        return True
    rendered_path = relative_path.removesuffix(".jinja")
    if rendered_path == "scripts/build.mjs" and answers.get("build_mode") != "bundle":
        return True
    return False


def _add_github_repo_topics(
    destination: Path,
    answers: Mapping[str, object],
    *,
    console: ConsoleLike,
) -> None:
    gh_executable = shutil.which("gh")
    if gh_executable is None:
        console.print("[yellow]GitHub CLI not found; skipping repository topic setup.[/yellow]")
        return

    command = [
        gh_executable,
        "repo",
        "edit",
        github_repository_target(answers, fallback_repo_name="pi-extension"),
    ]
    for topic in GITHUB_REPO_TOPICS:
        command.extend(["--add-topic", topic])

    result = subprocess.run(
        command,
        cwd=destination,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return

    details = result.stderr.strip() or result.stdout.strip() or "unknown error"
    console.print(f"[yellow]Failed to add GitHub repository topics: {details}[/yellow]")


def _run_npm(destination: Path, arguments: Sequence[str], *, action: str) -> None:
    npm_executable = shutil.which("npm")
    if npm_executable is None:
        raise RuntimeError("npm is required to generate a verified project")

    try:
        result = subprocess.run(
            [npm_executable, *arguments],
            cwd=destination,
            capture_output=True,
            text=True,
            check=False,
            timeout=300,
        )
    except subprocess.TimeoutExpired as cause:
        raise RuntimeError(f"Timed out while {action}") from cause
    if result.returncode != 0:
        output = "\n".join(
            section for section in (result.stdout.strip(), result.stderr.strip()) if section
        )
        raise RuntimeError(f"Failed while {action}: {output or 'unknown error'}")


def _install_generate_and_verify(destination: Path) -> list[Path]:
    # The generated prevalidation artifact does not exist until after dependencies are
    # installed. Suppress root lifecycle scripts for this first install, generate it,
    # then run the complete non-mutating verification before any git side effects.
    _run_npm(
        destination,
        ["install", "--ignore-scripts", "--no-audit", "--no-fund"],
        action="installing dependencies",
    )
    _run_npm(destination, ["run", "config:generate"], action="generating settings artifacts")
    _run_npm(destination, ["run", "verify"], action="verifying the generated project")

    expected = [
        Path("package-lock.json"),
        Path("config.schema.json"),
        Path("src/settings.prevalidated.ts"),
    ]
    missing = [str(path) for path in expected if not (destination / path).is_file()]
    if missing:
        raise RuntimeError(f"Project verification did not create: {', '.join(missing)}")
    return expected


def title(context: ManifestContext) -> str:
    return f"Generating a Pi extension package in {context.destination}"


def apply(context: ManifestContext) -> list[Path]:
    render_answers = _derived_answers(context.env, context.destination, context.answers)
    created = sprout_render_templates(
        context.env,
        context.template_dir,
        context.destination,
        render_answers,
        skip=should_skip_file,
        render_paths=True,
    )

    for generated_path in _install_generate_and_verify(context.destination):
        if generated_path not in created:
            created.append(generated_path)

    git_result = run_git_post_actions(
        context.destination,
        render_answers,
        console=sprout_console,
        commit_message="chore: initialize pi extension",
        fallback_repo_name="pi-extension",
        initial_branch="master",
    )
    if git_result.github_repository_created:
        _add_github_repo_topics(
            context.destination,
            render_answers,
            console=sprout_console,
        )

    return created


extensions = (
    GitDefaultsExtension,
    CurrentYearExtension,
)

template_dir = "template"

__all__ = [
    "apply",
    "extensions",
    "questions",
    "should_skip_file",
    "template_dir",
    "title",
]
