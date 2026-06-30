from __future__ import annotations

import re
import shutil
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Protocol

from jinja2 import Environment

from sprout import CurrentYearExtension, GitDefaultsExtension, ManifestContext, Question
from sprout.cli import render_templates as sprout_render_templates
from sprout.project import (
    SPDX_LICENSE_CHOICES,
    github_install_source,
    github_repository_target,
    github_repository_url,
    package_license_value,
    repository_git_url,
    run_git_post_actions,
    should_skip_license_file,
    validate_npm_package_name,
    validate_repository_name,
    validate_semver,
)
from sprout.prompt import console as sprout_console
from sprout.validators import validate_repository_url


class ConsoleLike(Protocol):
    def print(self, message: object) -> None: ...


WORKFLOW_CHOICES = [("ci", "GitHub Actions CI")]
GITHUB_REPO_TOPICS = ("pi", "pi-coding-agent", "pi-extension")

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
    username = str(env.globals.get("github_username") or "zigai").strip() or "zigai"
    return github_repository_url(username, repo)


def _installed_pi_version() -> str:
    pi_executable = shutil.which("pi")
    if pi_executable is None:
        return "0.80.2"

    result = subprocess.run(
        [pi_executable, "--version"],
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
    )
    version = result.stdout.strip().splitlines()[0] if result.stdout.strip() else ""
    return version if re.fullmatch(r"\d+\.\d+\.\d+", version) else "0.80.2"


def _package_name_without_scope(name: str) -> str:
    return name.rsplit("/", maxsplit=1)[-1]


def _package_keywords(answers: Mapping[str, object]) -> list[str]:
    repo_name = str(answers["repo_name"])
    feature = _strip_pi_prefix(repo_name)
    keywords = [*GITHUB_REPO_TOPICS, "pi-package"]
    if feature and feature not in keywords:
        keywords.append(feature)
    return sorted(keywords)


def _package_dependencies(_answers: Mapping[str, object]) -> list[tuple[str, str]]:
    return []


def _dev_dependencies(answers: Mapping[str, object]) -> list[tuple[str, str]]:
    pi_version = str(answers["pi_version"])
    dependencies = [
        ("@earendil-works/pi-coding-agent", f"^{pi_version}"),
        ("@types/node", "^24.10.1"),
        ("oxfmt", "^0.44.0"),
        ("oxlint", "^1.59.0"),
        ("oxlint-tsgolint", "^0.23.0"),
        ("tsx", "^4.22.3"),
        ("typescript", "^6.0.3"),
    ]
    return sorted(dependencies, key=lambda item: item[0])


def _peer_dependencies(_answers: Mapping[str, object]) -> list[tuple[str, str]]:
    return [("@earendil-works/pi-coding-agent", "*")]


def _pi_manifest_entries(_answers: Mapping[str, object]) -> list[tuple[str, list[str]]]:
    return [("extensions", ["./src/index.ts"])]


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
            "dev_dependencies": _dev_dependencies(answers),
            "github_install_source": github_install_source(
                repository_url,
                fallback=str(answers.get("repo_name") or "pi-extension"),
            ),
            "keywords": _package_keywords(answers),
            "license_value": package_license_value(answers.get("copyright_license")),
            "package_dependencies": _package_dependencies(answers),
            "package_name_unscoped": _package_name_without_scope(package_name),
            "peer_dependencies": _peer_dependencies(answers),
            "pi_manifest_entries": _pi_manifest_entries(answers),
            "repository_git_url": repository_git_url(repository_url),
            "repository_url": repository_url,
            "title_name": title_name,
        }
    )
    result.setdefault("github_workflows", [])
    result.setdefault("author_name", str(env.globals.get("git_user_name") or "zigai"))
    result.setdefault("destination_path", str(destination))
    return result


def questions(env: Environment, destination: Path) -> list[Question]:
    git_user_name = str(env.globals.get("git_user_name") or "")
    git_user_email = str(env.globals.get("git_user_email") or "")
    gh_available = shutil.which("gh") is not None
    npm_available = shutil.which("npm") is not None
    suggested_repo = _default_repo_name(destination)

    def default_package_name(answers: Mapping[str, object]) -> str:
        return suggested_repo

    def default_repo_name(answers: Mapping[str, object]) -> str:
        package_name = str(answers.get("package_name") or suggested_repo)
        return _kebab_case(_package_name_without_scope(package_name), fallback=suggested_repo)

    def default_description(answers: Mapping[str, object]) -> str:
        repo_name = str(answers.get("repo_name") or suggested_repo)
        feature = _strip_pi_prefix(repo_name).replace("-", " ")
        return f"Pi extension for {feature}."

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
            default=git_user_name or "zigai",
        ),
        Question(
            key="author_email",
            prompt="Author email",
            default=git_user_email or None,
        ),
        Question(
            key="description",
            prompt="Package description",
            default=default_description,
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
            prompt="Pi dev dependency version",
            help="Keep this aligned with the locally installed Pi version used for docs and checks.",
            default=_installed_pi_version(),
            validators=[validate_semver],
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
            key="create_package_lock",
            prompt="Create package-lock.json now?",
            help_text="Runs npm install --package-lock-only after rendering.",
            default=True,
            when=npm_available,
        ),
        Question.yes_no(
            key="create_github_repo",
            prompt="Create GitHub repository now?",
            help_text="Uses gh repo create after rendering and pushes the initial commit.",
            default=True,
            when=gh_available,
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


def _create_package_lock(destination: Path, *, console: ConsoleLike) -> Path | None:
    npm_executable = shutil.which("npm")
    if npm_executable is None:
        console.print("[yellow]npm is not installed; skipping package-lock.json creation.[/yellow]")
        return None

    result = subprocess.run(
        [npm_executable, "install", "--package-lock-only"],
        cwd=destination,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        lockfile = destination / "package-lock.json"
        return lockfile if lockfile.is_file() else None

    details = result.stderr.strip() or result.stdout.strip() or "unknown error"
    console.print(f"[yellow]Failed to create package-lock.json: {details}[/yellow]")
    return None


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

    if bool(render_answers.get("create_package_lock")):
        lockfile = _create_package_lock(context.destination, console=sprout_console)
        if lockfile is not None:
            created.append(lockfile.relative_to(context.destination))

    git_result = run_git_post_actions(
        context.destination,
        render_answers,
        console=sprout_console,
        commit_message="chore: initialize pi extension",
        fallback_repo_name="pi-extension",
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
