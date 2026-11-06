#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
if [ -z "${PYTHON:-}" ]; then
 for candidate in python3 python3.15 python3.14 python3.13 python3.12 python3.11; do
  if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; sys.exit(sys.version_info < (3, 11))'; then
   PYTHON=$(command -v "$candidate")
   export PYTHON
   break
  fi
 done
fi
[ -n "${PYTHON:-}" ] || { echo 'Native QEMU builds require Python 3.11 or newer.' >&2; exit 1; }
exec ./qemu/setup.sh
