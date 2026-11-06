#!/usr/bin/env python3
"""Check one-prompt error status on an isolated, logged-in QEMU console."""

import argparse
import json
import re
import time
import urllib.request

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--ui", required=True)
args = parser.parse_args()


def read(since=0):
    with urllib.request.urlopen(
        f"{args.ui}/console/read?since={since}", timeout=5
    ) as response:
        return json.load(response)


def command(text):
    offset = read()["end"]
    with urllib.request.urlopen(
        urllib.request.Request(args.ui + "/console/send", data=text.encode()), timeout=5
    ):
        pass
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        output = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", read(offset)["text"])
        if re.search(r"root@\S+ .*?>\s*$", output):
            return output
        time.sleep(0.05)
    raise AssertionError(f"No root prompt: {output!r}")


for failed, status in [("false", "!1"), ("__nest_missing_command__", "!127")]:
    output = command(failed)
    assert status in output, output
    output = command("")
    assert not re.search(r"!\d+", output), output
    assert "\x1b[1;32m" in read()["text"][-100:], "Prompt did not return to green"
assert "!1" in command("false")
assert "!1" not in command("true")
print("PASS: errors display once; Enter and successful commands restore green")
