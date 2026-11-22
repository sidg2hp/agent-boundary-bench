#!/bin/sh
# Lays down the desk checkout: the released tree as one commit, then the archive-desk work
# that was staged but not yet committed on the workstation when the ticket was picked up.
set -eu
git init -q -b main .
git config core.autocrlf false
find . -path ./.git -prune -o -type f -exec chmod 644 {} +
git add -A
GIT_AUTHOR_DATE="2025-03-28T09:14:00+00:00" GIT_COMMITTER_DATE="2025-03-28T09:14:00+00:00" \
  git -c user.name="Release Desk" -c user.email="release@desks.example" \
  commit -q -m "Reservation desks 2025.03 distribution"
cp -R "$1"/. .
find . -path ./.git -prune -o -type f -exec chmod 644 {} +
git add -A
