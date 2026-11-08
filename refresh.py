#!/usr/bin/env python3
"""刷新 WorkBuddy 凭据，写回同一个文件。

不需要 WorkBuddy 客户端，任何有 Python 3 的机器都能跑：

    python3 refresh.py -f ~/workbuddy.json
"""

import argparse
import errno
import json
import os
import ssl
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

# prefixPath /plugin 来自客户端 product.json 的 authentication.attributes.prefixPath
REFRESH_PATH = "/v2/plugin/auth/token/refresh"
DEFAULT_HOST = "https://www.workbuddy.cn"
DEFAULT_FILE = os.environ.get("WORKBUDDY_AUTH_FILE") or os.path.join(
    os.path.expanduser("~"), ".config", "workbuddy", "workbuddy.json")


def fail(message):
    print(json.dumps({"result": "ERROR", "report": message, "needs_attention": True},
                     ensure_ascii=False))
    sys.exit(1)


def days_left(ms):
    if not isinstance(ms, (int, float)) or ms <= 0:
        return None
    return (ms / 1000.0 - time.time()) / 86400.0


def fmt(ms):
    if not isinstance(ms, (int, float)) or ms <= 0:
        return "未知"
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(ms / 1000.0))


def save(path, data):
    """同目录临时文件 + rename；单文件 bind mount 无法 rename 时退回原地重写。"""
    directory = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".wb_refresh.")
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


def call(credential, refresh_token):
    auth = credential.get("auth") or {}
    host = auth.get("endpoint") or DEFAULT_HOST
    parts = urllib.parse.urlsplit(host)
    request = urllib.request.Request(
        parts.scheme + "://" + parts.netloc + REFRESH_PATH, data=b"{}", method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "WorkBuddy",
            "X-Refresh-Token": refresh_token,
            "X-Auth-Refresh-Source": "plugin",
            "X-Domain": auth.get("domain") or parts.hostname,
        })
    try:
        with urllib.request.urlopen(request, timeout=20,
                                    context=ssl.create_default_context()) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            body = json.loads(exc.read().decode("utf-8", "replace"))
            detail = " code=%s msg=%s" % (body.get("code"), str(body.get("msg"))[:160])
        except Exception:
            pass
        if exc.code in (401, 403):
            fail("刷新被拒绝（HTTP %d）%s。refresh token 无效或已过期，请重新导出。" % (exc.code, detail))
        fail("刷新失败（HTTP %d）%s" % (exc.code, detail))
    except urllib.error.URLError as exc:
        fail("连不上刷新接口（%s）" % exc.reason)
    except (ValueError, UnicodeError):
        fail("刷新接口返回的不是合法 JSON")

    if not isinstance(payload, dict) or payload.get("code") != 0:
        fail("刷新接口返回 code=%s，未取得新凭据" % (payload.get("code") if isinstance(payload, dict) else None))
    data = payload.get("data")
    if not isinstance(data, dict) or not data.get("accessToken"):
        fail("刷新接口响应里没有 accessToken")
    return data


def main():
    parser = argparse.ArgumentParser(description="刷新 WorkBuddy 凭据")
    parser.add_argument("-f", "--file", default=DEFAULT_FILE)
    parser.add_argument("--min-days", type=float, default=7.0,
                        help="剩余天数高于此值则跳过（默认 7）")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    try:
        with open(args.file, "r", encoding="utf-8") as handle:
            credential = json.load(handle)
    except FileNotFoundError:
        fail("凭据文件不存在：%s" % args.file)
    except ValueError:
        fail("凭据文件不是合法 JSON：%s" % args.file)

    auth = credential.get("auth") or {}
    old_refresh = auth.get("refreshToken")
    if not isinstance(old_refresh, str) or not old_refresh:
        fail("凭据文件里没有 refreshToken（旧格式导出文件可能没有），请重新导出。")

    remaining = days_left(auth.get("expiresAt"))
    if not args.force and remaining is not None and remaining > args.min_days:
        print(json.dumps({
            "result": "SKIPPED",
            "expires_at": fmt(auth.get("expiresAt")),
            "days_left": round(remaining, 1),
            "report": "还剩 %.1f 天，未到 %.0f 天阈值，本次不刷新" % (remaining, args.min_days),
        }, ensure_ascii=False))
        return

    data = call(credential, old_refresh)
    now = time.time() * 1000
    updated = dict(auth)
    updated["accessToken"] = data["accessToken"]
    if data.get("refreshToken"):
        updated["refreshToken"] = data["refreshToken"]
    if data.get("domain"):
        updated["domain"] = data["domain"]
    updated["tokenType"] = data.get("tokenType") or auth.get("tokenType") or "Bearer"
    for source, target in (("expiresIn", "expiresAt"), ("refreshExpiresIn", "refreshExpiresAt")):
        if isinstance(data.get(source), (int, float)) and data[source] > 0:
            updated[target] = int(now + data[source] * 1000)
    if isinstance(data.get("sessionState"), str):
        updated["sessionState"] = data["sessionState"]

    save(args.file, dict(credential, auth=updated))
    print(json.dumps({
        "result": "REFRESHED",
        "path": os.path.abspath(args.file),
        "expires_at": fmt(updated.get("expiresAt")),
        "refresh_expires_at": fmt(updated.get("refreshExpiresAt")),
        "report": "已刷新，valid until %s" % fmt(updated.get("expiresAt")),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
