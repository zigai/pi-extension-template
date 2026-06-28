from __future__ import annotations

import re
import shutil
import subprocess
from collections.abc import Callable, Mapping, Sequence
from datetime import date
from pathlib import Path
from typing import Protocol

from jinja2 import Environment
from jinja2.ext import Extension

from sprout import CurrentYearExtension, GitDefaultsExtension, Question
from sprout.cli import render_templates as sprout_render_templates
from sprout.validators import validate_repository_url


class ConsoleLike(Protocol):
    def print(self, message: object) -> None: ...


RenderTemplatesFn = Callable[..., list[Path]]


class PiTemplateExtension(Extension):
    def __init__(self, environment: Environment) -> None:
        super().__init__(environment)
        environment.globals["current_year"] = date.today().year


STARTER_KIND_CHOICES = [
    ("plain-command", "Plain slash command"),
    ("typed-command", "Typed slash command"),
    ("tool", "Model-callable tool"),
    ("lifecycle", "Lifecycle hook"),
]

RESOURCE_CHOICES = [
    ("skills", "Skills directory"),
    ("prompts", "Prompt templates directory"),
]

WORKFLOW_CHOICES = [("ci", "GitHub Actions CI")]

LICENSE_CHOICES = [
    ("MIT", "MIT License"),
    ("Apache-2.0", "Apache License 2.0"),
    ("None", "No license"),
]

PI_BUNDLED_PACKAGES = {
    "@earendil-works/pi-ai",
    "@earendil-works/pi-agent-core",
    "@earendil-works/pi-coding-agent",
    "@earendil-works/pi-tui",
    "typebox",
}


def _kebab_case(value: str, *, fallback: str) -> str:
    cleaned = re.sub(r"[^0-9a-zA-Z]+", "-", value).strip("-").lower()
    cleaned = re.sub(r"-+", "-", cleaned)
    if not cleaned:
        return fallback
    if cleaned[0].isdigit():
        return f"pi-{cleaned}"
    return cleaned


def _snake_case(value: str, *, fallback: str) -> str:
    cleaned = re.sub(r"[^0-9a-zA-Z]+", "_", value).strip("_").lower()
    cleaned = re.sub(r"_+", "_", cleaned)
    if not cleaned:
        return fallback
    if cleaned[0].isdigit():
        return f"tool_{cleaned}"
    return cleaned


def _title_case(value: str) -> str:
    words = re.split(r"[^0-9a-zA-Z]+", value)
    return " ".join(word.capitalize() for word in words if word)


def _strip_pi_prefix(value: str) -> str:
    return value[3:] if value.startswith("pi-") and len(value) > 3 else value


def _default_repo_name(destination: Path) -> str:
    repo = _kebab_case(destination.name, fallback="pi-extension")
    return repo if repo.startswith("pi-") else f"pi-{repo}"


def _default_feature_name(answers: Mapping[str, object], destination: Path) -> str:
    repo = str(answers.get("repo_name") or _default_repo_name(destination))
    return _strip_pi_prefix(_kebab_case(repo, fallback="extension"))


def _default_tool_name(answers: Mapping[str, object], destination: Path) -> str:
    return _snake_case(_default_feature_name(answers, destination), fallback="starter_tool")


def _default_repository_url(env: Environment, answers: Mapping[str, object], destination: Path) -> str:
    repo = str(answers.get("repo_name") or _default_repo_name(destination)).strip()
    username = str(env.globals.get("github_username") or "zigai").strip() or "zigai"
    return f"https://github.com/{username}/{repo}"


def _github_repo_target(answers: Mapping[str, object]) -> str:
    repository_url = str(answers.get("repository_url") or "").strip()
    match = re.match(
        r"^https://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?/?$",
        repository_url,
    )
    if match:
        return f"{match.group('owner')}/{match.group('repo')}"

    repo_name = str(answers.get("repo_name") or "").strip()
    return repo_name or "pi-extension"


def _is_github_repo_url(value: object) -> bool:
    return isinstance(value, str) and value.strip().startswith("https://github.com/")


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


def validate_package_name(value: str, _answers: Mapping[str, object]) -> tuple[bool, str | None]:
    name = value.strip()
    if not name:
        return False, "Package name is required."
    if not re.fullmatch(r"(?:@[a-z0-9][a-z0-9._-]*/)?[a-z0-9][a-z0-9._-]*", name):
        return False, "Package name must be a valid lowercase npm package name."
    return True, None


def validate_repo_name(value: str, _answers: Mapping[str, object]) -> tuple[bool, str | None]:
    name = value.strip()
    if not name:
        return False, "Repository name is required."
    if not re.fullmatch(r"[A-Za-z0-9._-]+", name):
        return False, "Repository name may only include letters, numbers, dots, underscores, and hyphens."
    return True, None


def validate_command_name(value: str, _answers: Mapping[str, object]) -> tuple[bool, str | None]:
    name = value.strip()
    if not re.fullmatch(r"[a-z][a-z0-9-]*", name):
        return False, "Command name must be lowercase kebab-case and start with a letter."
    return True, None


def validate_tool_name(value: str, _answers: Mapping[str, object]) -> tuple[bool, str | None]:
    name = value.strip()
    if not re.fullmatch(r"[a-z][a-z0-9_]*", name):
        return False, "Tool name must be lowercase snake_case and start with a letter."
    return True, None


def validate_pi_version(value: str, _answers: Mapping[str, object]) -> tuple[bool, str | None]:
    if re.fullmatch(r"\d+\.\d+\.\d+", value.strip()):
        return True, None
    return False, "Pi version must be a semantic version like 0.80.2."


def _package_name_without_scope(name: str) -> str:
    return name.rsplit("/", maxsplit=1)[-1]


def _package_keywords(answers: Mapping[str, object]) -> list[str]:
    repo_name = str(answers["repo_name"])
    feature = _strip_pi_prefix(repo_name)
    keywords = [
        "pi",
        "pi-coding-agent",
        "pi-extension",
        "pi-package",
    ]
    if feature and feature not in keywords:
        keywords.append(feature)
    return keywords


def _package_dependencies(answers: Mapping[str, object]) -> list[tuple[str, str]]:
    if answers.get("starter_kind") == "typed-command":
        return [("pi-typed-commands", "file:../pi-command-args")]
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
    if answers.get("starter_kind") == "tool":
        dependencies.append(("typebox", "1.1.38"))
    return sorted(dependencies, key=lambda item: item[0])


def _peer_dependencies(answers: Mapping[str, object]) -> list[tuple[str, str]]:
    peers = {"@earendil-works/pi-coding-agent"}
    if answers.get("starter_kind") == "tool":
        peers.add("typebox")
    return [(name, "*") for name in sorted(peers)]


def _pi_manifest_entries(answers: Mapping[str, object]) -> list[tuple[str, list[str]]]:
    entries = [("extensions", ["./src/index.ts"])]
    resource_types = set(_string_sequence(answers.get("resource_types")))
    if "skills" in resource_types:
        entries.append(("skills", ["./skills"]))
    if "prompts" in resource_types:
        entries.append(("prompts", ["./prompts"]))
    return entries


def _string_sequence(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, Sequence):
        return [item for item in value if isinstance(item, str)]
    return []


def _license_value(answers: Mapping[str, object]) -> str:
    license_name = str(answers.get("copyright_license") or "None")
    return "UNLICENSED" if license_name == "None" else license_name


def _repository_git_url(url: str) -> str:
    cleaned = url.rstrip("/")
    if cleaned.startswith("https://github.com/") and not cleaned.endswith(".git"):
        return f"git+{cleaned}.git"
    return f"git+{cleaned}"


def _github_install_source(answers: Mapping[str, object]) -> str:
    repository_url = str(answers.get("repository_url") or "").strip()
    match = re.match(r"^https://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?/?$", repository_url)
    if not match:
        return str(answers.get("repo_name") or "pi-extension")
    return f"github.com/{match.group('owner')}/{match.group('repo')}"


def _starter_readme(*, starter_kind: str, command_name: str, tool_name: str) -> str:
    if starter_kind == "plain-command":
        return (
            f"This template registers the `/{command_name}` slash command in `src/index.ts`.\n\n"
            "```text\n"
            f"/{command_name}\n"
            f"/{command_name} optional arguments\n"
            "```"
        )
    if starter_kind == "typed-command":
        return (
            f"This template registers the `/{command_name}` typed slash command in `src/index.ts` "
            "using `pi-typed-commands`.\n\n"
            "```text\n"
            f"/{command_name} world --loud\n"
            f"/{command_name} --help\n"
            "```"
        )
    if starter_kind == "tool":
        return f"This template registers the `{tool_name}` model-callable tool in `src/index.ts`."
    return "This template registers starter `session_start` and `session_shutdown` lifecycle hooks in `src/index.ts`."


def _resources_readme(*, resource_types: Sequence[str], skill_name: str, prompt_name: str) -> str:
    sections: list[str] = []
    if "skills" in resource_types:
        sections.append(
            "## Skills\n\n"
            f"This package includes `skills/{skill_name}/SKILL.md` as a starter Agent Skill."
        )
    if "prompts" in resource_types:
        sections.append(
            "## Prompts\n\n"
            f"This package includes `prompts/{prompt_name}.md` as a starter prompt template."
        )
    return "\n\n".join(sections)


def _derived_answers(
    env: Environment,
    destination: Path,
    answers: Mapping[str, object],
) -> dict[str, object]:
    package_name = str(answers["package_name"])
    repo_name = str(answers["repo_name"])
    feature_name = _strip_pi_prefix(repo_name)
    command_name = str(answers.get("command_name") or feature_name)
    tool_name = str(answers.get("tool_name") or _snake_case(feature_name, fallback="starter_tool"))
    title_name = _title_case(repo_name)
    repository_url = str(answers["repository_url"]).rstrip("/")
    starter_kind = str(answers["starter_kind"])
    skill_name = _kebab_case(feature_name, fallback="starter-skill")
    prompt_name = _kebab_case(feature_name, fallback="starter-prompt")
    resource_types = _string_sequence(answers.get("resource_types"))

    starter_readme = _starter_readme(
        starter_kind=starter_kind,
        command_name=command_name,
        tool_name=tool_name,
    )
    resources_readme = _resources_readme(
        resource_types=resource_types,
        skill_name=skill_name,
        prompt_name=prompt_name,
    )
    test_expected_exports: list[tuple[str, str]] = [
        ("packageName", package_name),
        ("extensionName", title_name),
        ("starterKind", starter_kind),
    ]
    test_import_names = ["extensionName", "packageName", "starterKind"]
    if starter_kind in {"plain-command", "typed-command"}:
        test_import_names.insert(0, "commandName")
        test_expected_exports.append(("commandName", command_name))
    if starter_kind == "tool":
        test_import_names.append("toolName")
        test_expected_exports.append(("toolName", tool_name))

    result: dict[str, object] = dict(answers)
    result.update(
        {
            "command_description": f"Run the {title_name} command.",
            "dev_dependencies": _dev_dependencies(answers),
            "github_install_source": _github_install_source(answers),
            "keywords": _package_keywords(answers),
            "license_value": _license_value(answers),
            "package_dependencies": _package_dependencies(answers),
            "package_name_unscoped": _package_name_without_scope(package_name),
            "peer_dependencies": _peer_dependencies(answers),
            "pi_manifest_entries": _pi_manifest_entries(answers),
            "prompt_name": prompt_name,
            "repository_git_url": _repository_git_url(repository_url),
            "repository_url": repository_url,
            "resource_types": resource_types,
            "resources_readme": resources_readme,
            "skill_name": skill_name,
            "starter_kind": starter_kind,
            "starter_readme": starter_readme,
            "test_expected_exports": test_expected_exports,
            "test_import_names": test_import_names,
            "title_name": title_name,
            "tool_description": f"Run the {title_name} starter tool.",
            "tool_label": _title_case(tool_name),
            "tool_name": tool_name,
            "tool_type_name": _title_case(tool_name).replace(" ", ""),
        }
    )
    result.setdefault("command_name", command_name)
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

    def default_command_name(answers: Mapping[str, object]) -> str:
        return _default_feature_name(answers, destination)

    def default_tool_name(answers: Mapping[str, object]) -> str:
        return _default_tool_name(answers, destination)

    return [
        Question(
            key="package_name",
            prompt="npm package name",
            help="Use the package name Pi should load from package.json.",
            default=default_package_name,
            validators=[validate_package_name],
        ),
        Question(
            key="repo_name",
            prompt="Repository name",
            help="Personal Pi extension repos usually start with pi-.",
            default=default_repo_name,
            validators=[validate_repo_name],
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
            key="starter_kind",
            prompt="Starter extension shape",
            choices=STARTER_KIND_CHOICES,
            default="plain-command",
        ),
        Question(
            key="command_name",
            prompt="Slash command name",
            default=default_command_name,
            validators=[validate_command_name],
            when=lambda answers: answers.get("starter_kind") in {"plain-command", "typed-command"},
        ),
        Question(
            key="tool_name",
            prompt="Tool name",
            default=default_tool_name,
            validators=[validate_tool_name],
            when=lambda answers: answers.get("starter_kind") == "tool",
        ),
        Question(
            key="resource_types",
            prompt="Additional Pi package resources",
            help="Optional conventional package resource directories to include.",
            choices=RESOURCE_CHOICES,
            multiselect=True,
            default=[],
        ),
        Question(
            key="pi_version",
            prompt="Pi dev dependency version",
            help="Keep this aligned with the locally installed Pi version used for docs and checks.",
            default=_installed_pi_version(),
            validators=[validate_pi_version],
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
            prompt="Create private GitHub repository now?",
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
    resource_types = set(_string_sequence(answers.get("resource_types")))
    github_workflows = set(_string_sequence(answers.get("github_workflows")))

    if relative_path == "LICENSE.jinja" and answers.get("copyright_license") == "None":
        return True
    if relative_path.startswith("skills/") and "skills" not in resource_types:
        return True
    if relative_path.startswith("prompts/") and "prompts" not in resource_types:
        return True
    if relative_path.startswith(".github/") and "ci" not in github_workflows:
        return True
    return False


def _ensure_git_repo(destination: Path, *, console: ConsoleLike) -> bool:
    git_executable = shutil.which("git")
    if git_executable is None:
        console.print("[yellow]Git is not installed; skipping local repository initialization.[/yellow]")
        return False

    if (destination / ".git").exists():
        return True

    result = subprocess.run(
        [git_executable, "init", "-b", "main"],
        cwd=destination,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return True

    fallback = subprocess.run(
        [git_executable, "init"],
        cwd=destination,
        check=False,
        capture_output=True,
        text=True,
    )
    if fallback.returncode == 0:
        subprocess.run([git_executable, "branch", "-M", "main"], cwd=destination, check=False)
        return True

    details = fallback.stderr.strip() or result.stderr.strip() or "unknown error"
    console.print(f"[yellow]Failed to initialize git repository: {details}[/yellow]")
    return False


def _has_git_commits(destination: Path, *, git_executable: str) -> bool:
    result = subprocess.run(
        [git_executable, "rev-parse", "--verify", "HEAD"],
        cwd=destination,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def _create_initial_commit(destination: Path, answers: Mapping[str, object], *, console: ConsoleLike) -> bool:
    git_executable = shutil.which("git")
    if git_executable is None:
        console.print("[yellow]Git is not installed; skipping initial commit.[/yellow]")
        return False
    if not _ensure_git_repo(destination, console=console):
        return False

    add_result = subprocess.run(
        [git_executable, "add", "--all"],
        cwd=destination,
        check=False,
        capture_output=True,
        text=True,
    )
    if add_result.returncode != 0:
        details = add_result.stderr.strip() or add_result.stdout.strip() or "unknown error"
        console.print(f"[yellow]Failed to stage files for initial commit: {details}[/yellow]")
        return _has_git_commits(destination, git_executable=git_executable)

    staged_diff_result = subprocess.run(
        [git_executable, "diff", "--cached", "--quiet", "--exit-code"],
        cwd=destination,
        check=False,
        capture_output=True,
        text=True,
    )
    if staged_diff_result.returncode == 0:
        return _has_git_commits(destination, git_executable=git_executable)
    if staged_diff_result.returncode != 1:
        details = staged_diff_result.stderr.strip() or staged_diff_result.stdout.strip() or "unknown error"
        console.print(f"[yellow]Failed to inspect staged changes: {details}[/yellow]")
        return _has_git_commits(destination, git_executable=git_executable)

    commit_command = [git_executable]
    author_name = str(answers.get("author_name") or "").strip()
    author_email = str(answers.get("author_email") or "").strip()
    if author_name:
        commit_command.extend(["-c", f"user.name={author_name}"])
    if author_email:
        commit_command.extend(["-c", f"user.email={author_email}"])
    commit_command.extend(["commit", "-m", "chore: initialize pi extension"])

    commit_result = subprocess.run(
        commit_command,
        cwd=destination,
        check=False,
        capture_output=True,
        text=True,
    )
    if commit_result.returncode == 0:
        return True

    details = commit_result.stderr.strip() or commit_result.stdout.strip() or "unknown error"
    console.print(f"[yellow]Failed to create initial commit: {details}[/yellow]")
    return _has_git_commits(destination, git_executable=git_executable)


def _create_github_repo(
    destination: Path,
    answers: Mapping[str, object],
    *,
    console: ConsoleLike,
    push: bool,
) -> None:
    gh_executable = shutil.which("gh")
    if gh_executable is None:
        console.print("[yellow]GitHub CLI not found; skipping repository creation.[/yellow]")
        return

    visibility = str(answers.get("github_repo_visibility") or "private").strip().lower()
    if visibility not in {"private", "public"}:
        visibility = "private"

    command = [gh_executable, "repo", "create", _github_repo_target(answers), f"--{visibility}"]
    description = str(answers.get("description") or "").strip()
    if description:
        command.extend(["--description", description])

    if _ensure_git_repo(destination, console=console):
        command.extend(["--source", str(destination), "--remote", "origin"])
        if push:
            command.append("--push")

    result = subprocess.run(command, cwd=destination, capture_output=True, text=True, check=False)
    if result.returncode == 0:
        return

    details = result.stderr.strip() or result.stdout.strip() or "unknown error"
    console.print(f"[yellow]Failed to create GitHub repository: {details}[/yellow]")


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


def title(destination: Path) -> str:
    return f"Generating a Pi extension package in {destination}"


def apply(
    *,
    env: Environment,
    template_dir: Path,
    destination: Path,
    answers: dict[str, object],
    console: ConsoleLike,
    render_templates: RenderTemplatesFn = sprout_render_templates,
) -> list[Path]:
    render_answers = _derived_answers(env, destination, answers)
    created = render_templates(
        env,
        template_dir,
        destination,
        render_answers,
        skip=should_skip_file,
        render_paths=True,
    )

    if bool(render_answers.get("create_package_lock")):
        lockfile = _create_package_lock(destination, console=console)
        if lockfile is not None:
            created.append(lockfile.relative_to(destination))

    if bool(render_answers.get("create_github_repo")):
        if not _is_github_repo_url(render_answers.get("repository_url")):
            console.print("[yellow]Repository URL is not a GitHub URL; gh will use the repo name.[/yellow]")
        has_commits = _create_initial_commit(destination, render_answers, console=console)
        _create_github_repo(destination, render_answers, console=console, push=has_commits)
    elif bool(render_answers.get("git_init")):
        _create_initial_commit(destination, render_answers, console=console)

    return created


extensions: Sequence[type[Extension]] = (
    GitDefaultsExtension,
    CurrentYearExtension,
    PiTemplateExtension,
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
