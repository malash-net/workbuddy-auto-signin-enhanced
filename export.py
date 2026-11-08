#!/usr/bin/env python3
"""从 WorkBuddy 桌面端导出明文凭据（含 refreshToken）。

必须在装了 WorkBuddy 客户端的机器上运行：token 是 $wbEncrypted 信封，
解密要走客户端的原生模块。

    python3 export.py -o ~/workbuddy.json
"""

import argparse
import errno
import importlib.util
import json
import os
import sys
import tempfile

DESKTOP = os.path.join("CodeBuddyExtension", "Data", "Public", "auth", "workbuddy-desktop.info")
DEFAULT_OUT = os.environ.get("WORKBUDDY_AUTH_FILE") or os.path.join(
    os.path.expanduser("~"), ".config", "workbuddy", "workbuddy.json")


def fail(message):
    print(json.dumps({"result": "ERROR", "report": message, "needs_attention": True},
                     ensure_ascii=False))
    sys.exit(1)


def save(path, data):
    """同目录临时文件 + rename；单文件 bind mount 无法 rename 时退回原地重写。"""
    directory = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".wb_export.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        try:
            os.replace(tmp, path)
        except OSError as exc:
            if exc.errno not in (errno.EBUSY, errno.EXDEV):
                raise
            os.unlink(tmp)
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(data, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def load_signin(repo):
    """按路径加载上游 signin.py，复用它已经验证过的解密 helper。"""
    path = os.path.join(os.path.abspath(os.path.expanduser(repo)), "signin.py")
    if not os.path.isfile(path):
        fail("没在 %s 找到 signin.py，请用 --repo 指定上游仓库" % repo)
    spec = importlib.util.spec_from_file_location("workbuddy_signin", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def find_repo(given):
    for candidate in (given, os.environ.get("WORKBUDDY_REPO"),
                      os.path.join(os.path.expanduser("~"), "Projects", "workbuddy-auto-signin"),
                      os.getcwd()):
        if candidate and os.path.isfile(os.path.join(candidate, "signin.py")):
            return candidate
    fail("找不到上游仓库（signin.py），请用 --repo 指定")


def find_desktop_auth(given):
    if given:
        return given
    home = os.path.expanduser("~")
    for base in (os.path.join(home, "Library", "Application Support"),
                 os.environ.get("LOCALAPPDATA") or os.path.join(home, "AppData", "Local")):
        path = os.path.join(base, DESKTOP)
        if os.path.isfile(path):
            return path
    fail("没找到 WorkBuddy 桌面端凭据文件，请用 --auth-file 指定")


def decrypt(module, value, label):
    if not isinstance(value, dict):
        if isinstance(value, str) and value:
            return value
        fail("%s 格式无法识别" % label)
    try:
        return module._run_auth_helper(module.find_workbuddy_runtime(),
                                       {"operation": "decrypt", "value": value})["accessToken"]
    except Exception as exc:
        fail("%s 解密失败（%s）" % (label, getattr(exc, "reason", type(exc).__name__)))


def main():
    parser = argparse.ArgumentParser(description="导出 WorkBuddy 明文凭据")
    parser.add_argument("-o", "--output", default=DEFAULT_OUT)
    parser.add_argument("--auth-file", help="桌面端凭据文件（默认自动探测）")
    parser.add_argument("--repo", help="上游仓库目录（含 signin.py）")
    args = parser.parse_args()

    module = load_signin(find_repo(args.repo))
    source = find_desktop_auth(args.auth_file)
    try:
        session = module.load_session(source)
    except Exception as exc:
        fail("读取桌面端凭据失败（%s）" % type(exc).__name__)

    auth = session.get("auth") or {}
    account = session.get("account") or {}
    out_auth = {
        "accessToken": decrypt(module, auth.get("accessToken"), "accessToken"),
        "refreshToken": decrypt(module, auth.get("refreshToken"), "refreshToken"),
        "tokenType": auth.get("tokenType") or "Bearer",
    }
    for field in ("domain", "endpoint", "expiresAt", "refreshExpiresAt"):
        if auth.get(field):
            out_auth[field] = auth[field]

    save(args.output, {"auth": out_auth, "account": {"uid": account.get("uid")}})
    print(json.dumps({
        "result": "EXPORTED",
        "path": os.path.abspath(args.output),
        "source": source,
        "report": "已导出明文凭据（含 refreshToken），等同账号凭证，请妥善保管",
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
