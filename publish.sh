#!/bin/bash
# Publish the elasticdash-python package to PyPI
# Usage: ./publish.sh

set -euo pipefail

# Load .env if present (expects PIPY_TOKEN=pypi-...)
if [ -f .env ]; then
	# shellcheck disable=SC2046
	export $(grep -v '^#' .env | xargs)
fi

: "${TWINE_USERNAME:=__token__}"
: "${TWINE_PASSWORD:=${PIPY_TOKEN:-}}"

if [ -z "${TWINE_PASSWORD}" ]; then
	echo "TWINE_PASSWORD (or PIPY_TOKEN) is not set. Export PIPY_TOKEN in .env or set TWINE_PASSWORD."
	exit 1
fi

echo "Using TWINE_USERNAME=${TWINE_USERNAME}"

# Clean previous builds
rm -rf dist build *.egg-info

# Build the package (source and wheel)
python3 -m build

# Upload to PyPI (requires twine)
twine upload dist/*

echo "\nPackage published to PyPI!"
