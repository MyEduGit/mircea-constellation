#!/usr/bin/env bash
set -u

cd /Users/mircea8me.com/mircea-constellation
mkdir -p "$HOME/backups"

if [ ! -d "$HOME/backups/mircea-constellation.git" ]; then
  git clone --bare . "$HOME/backups/mircea-constellation.git"
else
  git push "$HOME/backups/mircea-constellation.git" --all || true
fi

git config core.hooksPath .githooks
mkdir -p .githooks

cat > .githooks/post-commit <<'HOOK'
#!/usr/bin/env bash
cd /Users/mircea8me.com/mircea-constellation
bash preservation/run.sh --quick >/tmp/mircea_preservation_last.log 2>&1 || true
git push "$HOME/backups/mircea-constellation.git" --all >/tmp/mircea_mirror_last.log 2>&1 || true
HOOK

chmod +x .githooks/post-commit

echo "STATUS: PRESERVATION_INSTALL_COMPLETE"
echo "Mirror: $HOME/backups/mircea-constellation.git"
echo "Hook: .githooks/post-commit"
