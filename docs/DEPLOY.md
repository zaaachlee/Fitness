# AI Fitness Dashboard — 京东云部署指南（完整注释版）

> 每一行代码都有解释。`#` 后面是说明，**粗体**是需要你替换的内容。

---

## 〇、你需要准备什么

| 准备项 | 说明 |
|--------|------|
| 京东云账号 | 注册并实名认证 |
| 域名（可选） | 不想记 IP 就买个域名，约 ¥30/年 |
| 一个密码 | 自己设的数据库密码，牢记 |
| 电脑有 ssh 客户端 | Git Bash / PowerShell / 终端 都可以 |

---

## 一、购买服务器

打开 [京东云控制台](https://console.jdcloud.com/)，搜"轻量云主机"购买。

| 配置项 | 选什么 | 为什么 |
|--------|--------|--------|
| 地域 | 北京/上海/广州 | 离你近网速快 |
| 镜像 | Ubuntu 22.04 LTS | 本教程基于此系统 |
| 规格 | 2核 2GB | 够5人用 |
| 系统盘 | 40GB SSD | 代码+数据库+日志 |
| 带宽 | 3Mbps | 网页不卡的最低配置 |
| 防火墙 | 放开 22/80/443 | SSH连接/网页访问/HTTPS |

买完记下 **公网 IP**（在控制台能看到）。

---

## 二、连接服务器

```bash
# ssh = 安全远程连接工具
# root = 用 root 超级管理员身份登录
# @ = 连接到哪里
# 1.2.3.4 = 换成你在京东云控制台看到的公网 IP
ssh root@1.2.3.4

# 提示输入密码，输入时屏幕不显示任何字符（正常现象）
# 输入完直接按回车
```

进去后：

```bash
# apt = Ubuntu 的软件包管理器（类似手机上的应用商店）
# update = 刷新软件列表，看看有哪些更新
# && = 前一个命令成功后接着执行下一个
# upgrade = 把所有已安装的软件更新到最新版
# -y = 遇到询问是否继续时自动答"是"
apt update && apt upgrade -y
```

---

## 三、安装必要软件

### 3.1 PostgreSQL（数据库）

```bash
# apt install = 安装软件
# -y = 自动确认
# postgresql = 数据库服务程序
# postgresql-contrib = 数据库的附加工具包
apt install -y postgresql postgresql-contrib

# systemctl = 管理后台服务的工具
# start = 启动服务
# enable = 设为开机自启（服务器重启后自动运行）
systemctl start postgresql
systemctl enable postgresql

# sudo -u postgres = 用"postgres"这个数据库默认管理员身份执行命令
# psql = 进入 PostgreSQL 的命令行交互界面
# <<EOF ... EOF = 把中间的内容当作输入传给 psql
sudo -u postgres psql <<EOF
-- 创建用户，名字叫 fitness
-- WITH PASSWORD 'xxx' = 设密码，把 YourStrongPassword123! 换成你自己设的密码
-- 密码要有大小写字母+数字+符号，够复杂才安全
CREATE USER fitness WITH PASSWORD 'YourStrongPassword123!';
-- 创建数据库，名字叫 fitness_db，拥有者是 fitness 用户
CREATE DATABASE fitness_db OWNER fitness;
-- 把数据库的所有权限给 fitness 用户
GRANT ALL PRIVILEGES ON DATABASE fitness_db TO fitness;
-- 退出 psql
\q
EOF
# 到这里数据库就建好了，记住你的密码，后面配置要用
```

### 3.2 Python 3.12

```bash
# add-apt-repository = 添加一个第三方软件源
# ppa:deadsnakes/ppa = Python 官方维护的 Ubuntu 软件源
#（Ubuntu 自带的 Python 版本比较旧，这个源里有最新版）
add-apt-repository -y ppa:deadsnakes/ppa

# python3.12 = Python 解释器本体
# python3.12-venv = 虚拟环境工具（隔离项目依赖，避免和系统 Python 冲突）
# python3.12-dev = Python 开发头文件（安装某些包时需要）
apt install -y python3.12 python3.12-venv python3.12-dev
```

### 3.3 Node.js（前端运行时）

```bash
# curl = 下载文件的工具
# -fsSL = 静默下载，不显示进度条
# https://deb.nodesource.com/setup_22.x = Node.js 22.x 版本的官方安装脚本
# | bash - = 把下载的脚本直接交给 bash 执行
curl -fsSL https://deb.nodesource.com/setup_22.x | bash -

# 安装 Node.js（npm 会一起装好）
apt install -y nodejs

# 确认版本 >= 22
node --version
```

### 3.4 Nginx（网页服务器 / 反向代理）

```bash
# Nginx 的作用：接收来自互联网的请求（80端口），
# 根据请求路径转发给前端（3000端口）或后端（8000端口）
apt install -y nginx
systemctl start nginx
systemctl enable nginx
```

### 3.5 Git（拉代码）

```bash
apt install -y git
```

---

## 四、部署后端（FastAPI）

### 4.1 把项目上传到服务器

**在你的电脑上执行**（不是服务器），用 `scp` 上传整个项目文件夹：

```bash
# scp = 安全文件拷贝工具
# -r = 递归拷贝整个文件夹
# "d:/Zaaach vscode/ai-fitness-dashboard" = 你电脑上项目的路径
# root@1.2.3.4 = 服务器地址
# :/opt/fitness/ = 拷贝到服务器上的这个路径
scp -r "d:/Zaaach vscode/ai-fitness-dashboard" root@1.2.3.4:/opt/fitness/
```

如果你代码已经在 GitHub/Gitee 上，也可以直接在服务器上 clone：
```bash
# 在服务器上执行
git clone https://github.com/你的用户名/你的仓库.git /opt/fitness
```

### 4.2 配置后端环境变量

```bash
# 进入后端目录
cd /opt/fitness/backend

# cat > 文件名 <<'EOF' = 把下面内容写入文件，直到遇到 EOF 为止
# 'EOF' 加引号 = 不对 $() 等特殊符号做展开
cat > .env <<'EOF'
# 数据库连接地址（异步版，用于 FastAPI）
# postgresql+asyncpg://用户名:密码@地址:端口/数据库名
# localhost = 数据库在本机
DATABASE_URL=postgresql+asyncpg://fitness:YourStrongPassword123!@localhost:5432/fitness_db

# 数据库连接地址（同步版，用于 Alembic 迁移工具）
DATABASE_URL_SYNC=postgresql://fitness:YourStrongPassword123!@localhost:5432/fitness_db

# JWT 签名密钥（$(openssl rand -hex 32) 会生成一个32字节随机字符串）
# 这个密钥用来加密和验证登录 token，绝对不能泄露
SECRET_KEY=$(openssl rand -hex 32)

# JWT 加密算法
ALGORITHM=HS256

# access token 有效期（30分钟），过期后用 refresh token 换新的
ACCESS_TOKEN_EXPIRE_MINUTES=30

# refresh token 有效期（7天），用来免密刷新 access token
REFRESH_TOKEN_EXPIRE_DAYS=7

# AI 默认服务商（用户可以在设置页面自己覆盖）
# 这里先空着，用户登录后自己在设置页填 API Key
AI_PROVIDER=deepseek
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
OPENAI_BASE_URL=
OPENAI_MODEL=gpt-4o

# 关闭调试模式（生产环境不能开 debug）
DEBUG=false

# 允许哪些来源的请求（你的前端地址）
# 把"你的公网IP"替换成实际的 IP，例如 "http://123.45.67.89"
CORS_ORIGINS=["http://你的公网IP"]
EOF
```

**注意：把 `YourStrongPassword123!` 换成你 3.1 步设的数据库密码，把 `你的公网IP` 换成实际的公网 IP。**

### 4.3 安装依赖 & 初始化数据库

```bash
# python3.12 -m venv venv = 创建一个叫 venv 的虚拟环境文件夹
# 虚拟环境的作用：项目装的所有 Python 包都在这个文件夹里，不污染系统 Python
python3.12 -m venv venv

# source = 执行脚本（激活虚拟环境）
# 激活后，pip 和 python 都用虚拟环境里的版本
source venv/bin/activate

# 修复 requirements.txt（本地开发用了 SQLite，服务器要用 PostgreSQL）
# sed -i = 直接修改文件内容
# 's/旧内容/新内容/' = 替换文本
sed -i 's/# PostgreSQL only, not needed for SQLite//' requirements.txt
sed -i 's/psycopg2-binary.*/psycopg2-binary==2.9.10/' requirements.txt

# pip install = 安装 Python 包
# -r requirements.txt = 从文件里读取要装的包的列表
pip install -r requirements.txt

# 初始化数据库表结构 + 导入种子数据（食物库、动作库等）
python -m app.seed.run

# 测试启动（跑一下看看有没有报错）
# --host 0.0.0.0 = 允许来自任何 IP 的请求（测试用）
# --port 8000 = 监听 8000 端口
uvicorn app.main:app --host 0.0.0.0 --port 8000
# 看到 "Application startup complete." 就按 Ctrl+C 停止
```

### 4.4 把后端设为系统服务（守护进程）

```bash
# 把下面的配置写入 /etc/systemd/system/fitness-api.service
# systemd = Linux 的服务管理系统（负责后台运行、开机自启、崩溃重启）
cat > /etc/systemd/system/fitness-api.service <<'EOF'
[Unit]
# 描述这个服务是干什么的
Description=AI Fitness Dashboard API
# 在什么之后启动（网络和数据库就绪后才启动）
After=network.target postgresql.service

[Service]
# 以 root 用户运行
User=root
# 工作目录
WorkingDirectory=/opt/fitness/backend
# 启动命令（用虚拟环境里的 uvicorn）
# --host 127.0.0.1 = 只监听本地，由 Nginx 对外暴露（更安全）
# --port 8000 = 监听 8000 端口
ExecStart=/opt/fitness/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
# 崩溃后自动重启
Restart=always
# 等 5 秒再重启（防止频繁重启）
RestartSec=5

[Install]
# 开机自启
WantedBy=multi-user.target
EOF

# daemon-reload = 重新加载 systemd 配置文件
systemctl daemon-reload
# 启动服务
systemctl start fitness-api
# 设为开机自启
systemctl enable fitness-api
# 查看状态（确认 active (running) 就表示成功）
systemctl status fitness-api
```

---

## 五、部署前端（Next.js）

### 5.1 构建生产版本

```bash
# 进入前端目录
cd /opt/fitness/frontend

# npm ci = 按照 package-lock.json 精确安装依赖
#（比 npm install 更快更可靠，适合部署）
npm ci

# 创建前端的环境变量文件
# NEXT_PUBLIC_API_URL = 前端发给后端的 API 地址
# 把"你的公网IP"换成实际IP
cat > .env.local <<'EOF'
NEXT_PUBLIC_API_URL=http://你的公网IP:8000/api/v1
EOF

# npm run build = 编译 TypeScript + 打包优化 + 生成静态资源
# 产物在 .next/ 目录
npm run build
```

### 5.2 把前端设为系统服务

```bash
cat > /etc/systemd/system/fitness-web.service <<'EOF'
[Unit]
Description=AI Fitness Dashboard Web
After=network.target

[Service]
User=root
WorkingDirectory=/opt/fitness/frontend
# npm start = 启动生产模式的 Next.js 服务器
ExecStart=/usr/bin/npm start
Restart=always
RestartSec=5
# NODE_ENV=production = 告诉 Node.js 这是生产环境（关闭调试信息）
Environment=NODE_ENV=production
# 监听 3000 端口
Environment=PORT=3000

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl start fitness-web
systemctl enable fitness-web
systemctl status fitness-web
```

---

## 六、配置 Nginx（统一入口）

Nginx 的作用：用户访问 `http://你的IP` → Nginx（80端口）→ 根据路径分发：
- `/` → 转发给前端 3000 端口
- `/api/` → 转发给后端 8000 端口

```bash
# 写入 Nginx 配置文件
cat > /etc/nginx/sites-available/fitness <<'EOF'
server {
    # 监听 80 端口（HTTP 标准端口）
    listen 80;
    # 你的域名或 IP（把"你的公网IP"换成实际值）
    server_name 你的公网IP;

    # 允许上传的最大文件大小（为以后图片识别预留）
    client_max_body_size 20M;

    # 处理前端请求：路径是 / 开头的都转发给前端
    location / {
        # 代理转发到本机 3000 端口（Next.js）
        proxy_pass http://127.0.0.1:3000;
        # 支持 WebSocket（Next.js 热更新需要）
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        # 把原始请求的域名/IP 传给后端
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    # 处理后端请求：路径是 /api/ 开头的都转发给后端
    location /api/ {
        # 代理转发到本机 8000 端口（FastAPI）
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# ln -sf = 创建符号链接（软链接）
# 把 sites-available 里的配置文件链接到 sites-enabled
# Nginx 只加载 sites-enabled 里的配置
ln -sf /etc/nginx/sites-available/fitness /etc/nginx/sites-enabled/
# 删除默认站点配置（避免冲突）
rm -f /etc/nginx/sites-enabled/default

# 检查 Nginx 配置语法有没有错误
nginx -t
# 重新加载 Nginx（应用新配置，不中断服务）
systemctl reload nginx
```

---

## 七、SSL 证书（HTTPS）

**有域名才需要做这一步。** 没有域名的话跳过，用 `http://你的IP` 也能正常使用。

```bash
# certbot = Let's Encrypt 免费 SSL 证书工具
# python3-certbot-nginx = certbot 的 Nginx 插件
apt install -y certbot python3-certbot-nginx

# 自动获取证书并配置 Nginx
# -d your-domain.com = 把 your-domain.com 换成你的域名
certbot --nginx -d your-domain.com
# 按提示：输入邮箱 → 同意条款 → 选择是否自动重定向 HTTP 到 HTTPS（选2）

# 证书有效期90天，certbot 会自动续期（已加入系统定时任务）
```

---

## 八、验证部署

在浏览器打开 `http://你的公网IP`：

| 检查项 | 预期 | 不对怎么办 |
|--------|------|-----------|
| 能看到登录页 | 部署成功 | — |
| 注册账号成功 | 后端 OK | `systemctl status fitness-api` 看日志 |
| 登录后各页面正常 | 全部 OK | `journalctl -u fitness-web -n 50` 看日志 |

**如果打不开：**
```bash
# 1. 确认服务在运行
systemctl status fitness-api fitness-web
# 应该都是 active (running)

# 2. 确认 Nginx 在监听 80 端口
# netstat = 查看网络连接，-tlnp = 只看正在监听的 TCP 端口
# grep = 过滤关键字
netstat -tlnp | grep -E "3000|8000|80"

# 3. 确认京东云防火墙放开了 80 端口
#（控制台 → 轻量云主机 → 防火墙 → 检查入方向规则）

# 4. 看后端日志（最近50行）
journalctl -u fitness-api -n 50
# 看前端日志
journalctl -u fitness-web -n 50
```

---

## 九、日常维护

```bash
# ===== 更新代码后重启服务 =====
cd /opt/fitness
git pull                                # 拉取最新代码
cd frontend
npm ci && npm run build                 # 重新安装依赖 + 构建
systemctl restart fitness-web           # 重启前端（新代码生效）
cd /opt/fitness/backend
source venv/bin/activate
pip install -r requirements.txt         # 更新 Python 依赖（如果有新包）
systemctl restart fitness-api           # 重启后端

# ===== 数据库备份 =====
mkdir -p /opt/backup
# pg_dump = 导出 PostgreSQL 数据库
# -U fitness = 用 fitness 用户连接
# fitness_db = 数据库名
# $(date +%Y%m%d) = 当前日期，如 20260705
# > 文件路径 = 把输出写入文件
pg_dump -U fitness fitness_db > /opt/backup/fitness_$(date +%Y%m%d).sql

# ===== 设置每天自动备份 =====
# crontab -e = 编辑定时任务
# 添加这一行（每天凌晨2点执行）：
# 0 2 * * * pg_dump -U fitness fitness_db > /opt/backup/fitness_$(date +%Y%m%d).sql
```

---

*最后更新: 2026-07-05*
