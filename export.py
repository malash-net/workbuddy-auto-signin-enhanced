#!/usr/bin/env python3
"""从 WorkBuddy 桌面端导出明文凭据（含 refreshToken）。

需在装了 WorkBuddy 客户端的机器上运行 —— token 是 $wbEncrypted 信封，
解密要走客户端的原生模块。

    python3 export.py -o ~/workbuddy.json
"""

import argparse
import importlib.util
import json
import os
import sys

DESKTOP = "CodeBuddyExtension/Data/Public/auth/workbuddy-desktop.info"
DEFAULT_OUT = os.environ.get("WORKBUDDY_AUTH_FILE") or os.path.expanduser(
    "~/.config/workbuddy/workbuddy.json")


def load_signin(repo):
    repo = repo or os.environ.get("WORKBUDDY_REPO") or os.path.expanduser(
        "~/Projects/workbuddy-auto-signin")
    spec = importlib.util.spec_from_file_location("signin", os.path.join(repo, "signin.py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules["signin"] = module
    spec.loader.exec_module(module)
    return module


def desktop_auth_file():
    home = os.path.expanduser("~")
    for base in (os.path.join(home, "Library", "Application Support"),
                 os.environ.get("LOCALAPPDATA") or os.path.join(home, "AppData", "Local")):
        path = os.path.join(base, DESKTOP)
        if os.path.exists(path):
            return path
    sys.exit("找不到 WorkBuddy 桌面端凭据文件")


def decrypt(signin, value):
    if not isinstance(value, dict):
        return value
    return signin._run_auth_helper(signin.find_workbuddy_runtime(),
                                   {"operation": "decrypt", "value": value})["accessToken"]


def main():
    parser = argparse.ArgumentParser(description="导出 WorkBuddy 明文凭据")
    parser.add_argument("-o", "--output", default=DEFAULT_OUT)
    parser.add_argument("--repo", help="上游仓库目录（含 signin.py）")
    parser.add_argument("--auth-file", help="桌面端凭据文件")
    args = parser.parse_args()

    signin = load_signin(args.repo)
    session = signin.load_session(args.auth_file or desktop_auth_file())
    auth = session["auth"]

    credential = {
        "auth": {
            "accessToken": decrypt(signin, auth["accessToken"]),
            "refreshToken": decrypt(signin, auth["refreshToken"]),
            "domain": auth.get("domain"),
        },
        "account": {"uid": session["account"]["uid"]},
    }
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(credential, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    json.dump({"result": "EXPORTED", "path": args.output},
              sys.stdout, ensure_ascii=False)
    print()


if __name__ == "__main__":
    main()
