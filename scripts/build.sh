#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
board=diamond3
if [ "${1:-}" = --board ]; then board=$2; shift 2; fi
case "$board" in diamond3|j49) ;; *) echo "Unknown board: $board" >&2; exit 1;; esac
make prepare
docker build -t diamond3-buildroot .
docker volume create diamond3-systemd-output >/dev/null
[ "$#" -gt 0 ] || set -- all
if [ "$board" = j49 ]; then
 if ! docker run --rm -v diamond3-systemd-output:/src/output diamond3-buildroot test -x /src/output/host/bin/arm-buildroot-linux-gnueabihf-gcc; then
  docker run --rm -v "$PWD:/src" -v diamond3-systemd-output:/src/output diamond3-buildroot make diamond3-defconfig toolchain
 fi
 docker volume create j49-systemd-output >/dev/null
 docker run --rm -v "$PWD:/src" -v diamond3-systemd-output:/src/output -v j49-systemd-output:/src/output/j49 diamond3-buildroot make BOARD=j49 "$@"
 mkdir -p output/j49/images
 docker run --rm -v "$PWD:/export" -v j49-systemd-output:/build diamond3-buildroot sh -c 'cp -a /build/images/. /export/output/j49/images/'
 exit 0
fi
docker run --rm -v "$PWD:/src" -v diamond3-systemd-output:/src/output diamond3-buildroot make "$@"
mkdir -p output/images
docker run --rm -v "$PWD:/export" -v diamond3-systemd-output:/build diamond3-buildroot sh -c 'cp -a /build/images/. /export/output/images/'
