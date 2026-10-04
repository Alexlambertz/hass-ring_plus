#!/bin/sh
# Build dist/ring_plus: the integration with aioring bundled inside (no PyPI needed).
set -e
cd "$(dirname "$0")/.."
rm -rf dist && mkdir -p dist
cp -R custom_components/ring_plus dist/ring_plus
find dist -name __pycache__ -prune -exec rm -rf {} +
cp -R aioring/aioring dist/ring_plus/aioring
find dist -name __pycache__ -prune -exec rm -rf {} +
for f in dist/ring_plus/*.py; do
  sed -i.bak -E 's/^from aioring\.devices import/from .aioring.devices import/; s/^from aioring import/from .aioring import/' "$f"
  rm "$f.bak"
done
(cd dist && tar czf ring_plus.tar.gz ring_plus)
# HACS release asset: zip root = the integration files themselves
(cd dist/ring_plus && zip -qr ../ring_plus.zip .)
echo "built dist/ring_plus.tar.gz and dist/ring_plus.zip"
