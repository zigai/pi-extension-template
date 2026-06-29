fmt:
    python -m py_compile sprout.py

lint:
    python -m py_compile sprout.py

test:
    rm -rf .tmp/pi-template-smoke
    sprout . .tmp/pi-template-smoke --force \
        --package-name pi-template-smoke \
        --repo-name pi-template-smoke \
        --author-name zigai \
        --author-email zigai@example.invalid \
        --description "Smoke-test Pi extension." \
        --repository-url https://github.com/zigai/pi-template-smoke \
        --starter-kind plain-command \
        --command-name template-smoke \
        --pi-version 0.80.2 \
        --copyright-license BSD-3-Clause \
        --github-workflows ci \
        --create-package-lock no \
        --create-github-repo no \
        --git-init no
    grep -q 'BSD 3-Clause License' .tmp/pi-template-smoke/LICENSE
    grep -q '"license": "BSD-3-Clause"' .tmp/pi-template-smoke/package.json
    python -c 'import json; from pathlib import Path; data = json.loads(Path(".tmp/pi-template-smoke/package.json").read_text()); keywords = set(data["keywords"]); assert {"pi", "pi-coding-agent", "pi-extension"} <= keywords'
    rm -rf .tmp/pi-template-topic-gh .tmp/fake-gh-bin .tmp/gh-calls
    python -c 'from pathlib import Path; root = Path.cwd(); bin_dir = root / ".tmp/fake-gh-bin"; bin_dir.mkdir(parents=True, exist_ok=True); calls = root / ".tmp/gh-calls"; gh = bin_dir / "gh"; gh.write_text("#!/bin/sh\necho \"$*\" >> " + str(calls) + "\nexit 0\n"); gh.chmod(0o755)'
    PATH="$(pwd)/.tmp/fake-gh-bin:$PATH" sprout . .tmp/pi-template-topic-gh --force \
        --package-name pi-template-topic-gh \
        --repo-name pi-template-topic-gh \
        --author-name zigai \
        --author-email zigai@example.invalid \
        --description "Topic smoke-test Pi extension." \
        --repository-url https://github.com/zigai/pi-template-topic-gh \
        --starter-kind plain-command \
        --command-name template-topic-gh \
        --pi-version 0.80.2 \
        --copyright-license MIT \
        --github-workflows ci \
        --create-package-lock no \
        --create-github-repo yes \
        --github-repo-visibility private
    grep -q '^repo edit zigai/pi-template-topic-gh --add-topic pi --add-topic pi-coding-agent --add-topic pi-extension$' .tmp/gh-calls

fix: fmt
