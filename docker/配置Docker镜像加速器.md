# 配置 Docker 镜像加速器

由于网络原因，拉取 Docker Hub 镜像可能较慢或失败。请按照以下步骤配置 Docker 镜像加速器。

## Windows (Docker Desktop)

1. 打开 Docker Desktop
2. 点击右上角的 **设置** (Settings) 图标
3. 选择 **Docker Engine**
4. 在 JSON 配置中添加以下内容：

```json
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com",
    "https://mirror.baidubce.com"
  ]
}
```

5. 点击 **Apply & Restart** 应用并重启

## Linux

1. 创建或编辑 `/etc/docker/daemon.json`：

```bash
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json <<-'EOF'
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com",
    "https://mirror.baidubce.com"
  ]
}
EOF
```

2. 重启 Docker 服务：

```bash
sudo systemctl daemon-reload
sudo systemctl restart docker
```

## macOS (Docker Desktop)

1. 打开 Docker Desktop
2. 点击菜单栏的 **Docker** → **Preferences** (或 **Settings**)
3. 选择 **Docker Engine**
4. 在 JSON 配置中添加镜像加速器配置（同 Windows）
5. 点击 **Apply & Restart**

## 验证配置

运行以下命令验证配置是否生效：

```bash
docker info | grep -A 10 "Registry Mirrors"
```

如果看到配置的镜像地址，说明配置成功。

## 其他镜像加速器

如果上述镜像源不可用，可以尝试：

- **阿里云镜像加速器**（需要登录阿里云获取专属地址）：
  - 访问：https://cr.console.aliyun.com/cn-hangzhou/instances/mirrors
  - 获取专属加速地址，格式：`https://<your-id>.mirror.aliyuncs.com`

- **腾讯云镜像加速器**：
  - `https://mirror.ccs.tencentyun.com`

配置完成后，重新尝试构建：

```bash
docker compose build frontend
```

