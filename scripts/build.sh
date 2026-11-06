#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
make prepare
docker build -t diamond3-buildroot .
docker volume create diamond3-buildroot-output >/dev/null
[ "$#" -gt 0 ] || set -- all
docker run --rm -v "$PWD:/src" -v diamond3-buildroot-output:/src/output diamond3-buildroot make "$@"
mkdir -p output/images
docker run --rm -v "$PWD:/export" -v diamond3-buildroot-output:/build diamond3-buildroot sh -c 'cp -a /build/images/. /export/output/images/'
