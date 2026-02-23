#!/bin/bash
# Publish the elasticdash-python package to PyPI
# Usage: ./publish.sh

set -e

# Clean previous builds
rm -rf dist build *.egg-info

# Build the package (source and wheel)
python3 -m build

# Upload to PyPI (requires twine)
twine upload dist/*

echo "\nPackage published to PyPI!"
