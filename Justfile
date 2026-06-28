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
        --resource-types skills \
        --pi-version 0.80.2 \
        --copyright-license MIT \
        --github-workflows ci \
        --create-package-lock no \
        --create-github-repo no \
        --git-init no

fix: fmt
