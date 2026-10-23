#!/bin/sh
# Builds the client into the app as a step of Xcode's own build, before it packs the files
# (ADR-0033): the "App (Local)" scheme (Debug) against the API on this Mac, "App
# (Production)" (Release) against production. A failed client build fails the app's, so a
# build never carries a stale client or the wrong server.
set -e

# Xcode runs scripts without the login shell's PATH: find Node as the terminal does.
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

cd "$SRCROOT/../.."
if [ "$CONFIGURATION" = "Release" ]; then
  npm run app:ios:prod
else
  npm run app:ios:local
fi
