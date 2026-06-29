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

fix: fmt
