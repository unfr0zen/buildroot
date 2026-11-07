#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
started=$(date +%s)
board=diamond3
if [ "${1:-}" = --board ]; then board=$2; shift 2; fi
case "$board" in diamond3|j49|onyx) ;; *) echo "Unknown board: $board" >&2; exit 1;; esac
make prepare
docker build -t diamond3-buildroot .
docker volume create diamond3-systemd-output >/dev/null
[ "$#" -gt 0 ] || set -- all
if [ "$board" != diamond3 ]; then
 if ! docker run --rm -v diamond3-systemd-output:/src/output diamond3-buildroot test -x /src/output/host/bin/arm-buildroot-linux-gnueabihf-gcc; then
  docker run --rm -v "$PWD:/src" -v diamond3-systemd-output:/src/output diamond3-buildroot make diamond3-defconfig toolchain
 fi
 docker volume create ${board}-systemd-output >/dev/null
 docker run --rm -v "$PWD:/src" -v diamond3-systemd-output:/src/output -v ${board}-systemd-output:/src/output/$board diamond3-buildroot make BOARD="$board" BUILD_SUMMARY=0 "$@"
 mkdir -p output/$board/images
 docker run --rm -v "$PWD:/export" -v ${board}-systemd-output:/build diamond3-buildroot sh -c 'cp -a /build/images/. /export/output/"$1"/images/' sh "$board"
 python3 scripts/build-summary.py --board "$board" --images output/$board/images --started "$started" --copied
 exit 0
fi
docker run --rm -v "$PWD:/src" -v diamond3-systemd-output:/src/output diamond3-buildroot make BUILD_SUMMARY=0 "$@"
mkdir -p output/images
docker run --rm -v "$PWD:/export" -v diamond3-systemd-output:/build diamond3-buildroot sh -c 'cp -a /build/images/. /export/output/images/'
python3 scripts/build-summary.py --board diamond3 --images output/images --started "$started" --copied
