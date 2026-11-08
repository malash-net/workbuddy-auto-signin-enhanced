# workbuddy-auto-signin-enhanced

[English](./README.md) | [中文](./README.zh-CN.md)

> **⚠️ 由 AI 辅助编写，请谨慎使用。**
> 本项目通过 AI 辅助的"氛围编程"构建，未经过生产环境审计。部署到关键场景前请仔细审查。

在 Docker 里运行 [workbuddy-auto-signin](https://github.com/88lin/workbuddy-auto-signin)，适用于没有桌面客户端的机器。上游代码在构建时克隆，不做任何修改。

## 使用

签到（默认 `auto`）：

```bash
docker run --rm -v /srv/workbuddy:/auth \
  ghcr.io/malash-net/workbuddy-auto-signin-enhanced:latest
```

其他动作直接透传：

```bash
docker run --rm -v /srv/workbuddy:/auth \
  ghcr.io/malash-net/workbuddy-auto-signin-enhanced:latest status
```

定时运行：

```cron
5 0 * * * docker run --rm -v /srv/workbuddy:/auth ghcr.io/malash-net/workbuddy-auto-signin-enhanced:latest >> /var/log/wb.log 2>&1
10 8 * * * docker run --rm --entrypoint python3 -v /srv/workbuddy:/auth ghcr.io/malash-net/workbuddy-auto-signin-enhanced:latest refresh.py >> /var/log/wb-refresh.log 2>&1
```

挂载**目录**，不要挂单个文件。

## 导出凭据

在装了 WorkBuddy 客户端的机器上运行：

```bash
python3 export.py -o ~/workbuddy.json
scp ~/workbuddy.json nas:/srv/workbuddy/workbuddy.json
rm ~/workbuddy.json
```

## 续期

```bash
python3 refresh.py -f ~/workbuddy.json           # 剩余 >7 天时跳过
python3 refresh.py -f ~/workbuddy.json --force
```

或在镜像里：

```bash
docker run --rm --entrypoint python3 -v /srv/workbuddy:/auth \
  ghcr.io/malash-net/workbuddy-auto-signin-enhanced:latest refresh.py
```

## 配置

| 环境变量 | 默认值 | 说明 |
| --- | --- | --- |
| `WORKBUDDY_AUTH_FILE` | `/auth/workbuddy.json` | 两个脚本读写的凭据文件 |

## 安全

`workbuddy.json` 里是明文 token，等同于密码。请勿提交进 git 或放在公共目录，导出后的副本传完就删。

## 许可证

[MIT](./LICENSE)
