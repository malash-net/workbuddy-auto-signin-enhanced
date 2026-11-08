#!/usr/bin/env python3
"""刷新 WorkBuddy 凭据，写回同一个文件。

    python3 refresh.py -f ~/workbuddy.json
"""

import argparse
import json
import os
import sys
import time
import urllib.request

# /plugin 这一段是客户端 product.json 里的 authentication.attributes.prefixPath
URL = "https://www.workbuddy.cn/v2/plugin/auth/token/refresh"
DEFAULT_FILE = os.environ.get("WORKBUDDY_AUTH_FILE") or os.path.expanduser(
    "~/.config/workbuddy/workbuddy.json")


def main():
    parser = argparse.ArgumentParser(description="刷新 WorkBuddy 凭据")
    parser.add_argument("-f", "--file", default=DEFAULT_FILE)
    args = parser.parse_args()

    with open(args.file, encoding="utf-8") as handle:
        credential = json.load(handle)
    auth = credential["auth"]

    request = urllib.request.Request(URL, data=b"{}", method="POST", headers={
        "Content-Type": "application/json",
        "X-Refresh-Token": auth["refreshToken"],
        "X-Auth-Refresh-Source": "plugin",
        "X-Domain": auth.get("domain") or "www.workbuddy.cn",
    })
    with urllib.request.urlopen(request) as response:
        data = json.load(response)["data"]

    now = int(time.time() * 1000)
    auth["accessToken"] = data["accessToken"]
    auth["refreshToken"] = data.get("refreshToken", auth["refreshToken"])
    auth["expiresAt"] = now + data["expiresIn"] * 1000
    auth["refreshExpiresAt"] = now + data["refreshExpiresIn"] * 1000

    with open(args.file, "w", encoding="utf-8") as handle:
        json.dump(credential, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    json.dump({"result": "REFRESHED", "expiresAt": auth["expiresAt"]},
              sys.stdout, ensure_ascii=False)
    print()


if __name__ == "__main__":
    main()
