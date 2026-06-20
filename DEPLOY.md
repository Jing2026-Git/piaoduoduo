# 🚀 Railway 部署指南

Railway 是一个现代化的云平台，对 Flask 应用有很好的支持，而且有免费额度。

## 方式一：从 GitHub 一键部署（推荐）

### 步骤 1：访问 Railway
点击下面的链接：

👉 **https://railway.app/new**

### 步骤 2：连接 GitHub
1. 点击 "Login with GitHub"
2. 授权 Railway 访问您的 GitHub 账号
3. 选择仓库：`Jing2026-Git/piaoduoduo`

### 步骤 3：配置部署
Railway 会自动检测这是一个 Python Flask 项目，无需额外配置！

### 步骤 4：部署完成
- Railway 会自动：
  - 安装依赖（从 requirements.txt）
  - 启动 Gunicorn 服务器
  - 分配一个公共 URL

部署完成后，您会获得类似这样的链接：
```
https://piaoduoduo.up.railway.app
```

---

## 方式二：使用 Railway CLI

```bash
# 1. 安装 Railway CLI
npm install -g @railway/cli

# 2. 登录
railway login

# 3. 进入项目目录
cd /workspace/piaoduoduo

# 4. 初始化项目（选择已有 GitHub repo）
railway init

# 5. 部署
railway up

# 6. 获取访问链接
railway status
```

---

## 方式三：直接推送部署

```bash
# 1. 安装 Railway CLI
npm install -g @railway/cli

# 2. 登录并关联项目
cd /workspace/piaoduoduo
railway login
railway link <your-project-id>

# 3. 推送部署
git add .
git commit -m "准备 Railway 部署"
git push origin master

# Railway 会自动检测并部署
```

---

## ✅ 验证部署

部署成功后，访问 Railway 提供的 URL，例如：
```
https://piaoduoduo.railway.app
```

测试功能：
- 首页：`/`
- 搜索：`/search?keyword=周杰伦`
- API：`/api/search?keyword=演唱会`

---

## 📊 Railway 免费额度

| 资源 | 免费额度 |
|-----|---------|
| 每月运行时间 | 500 小时 |
| 内存 | 512 MB |
| 磁盘空间 | 1 GB |
| 数据库 | 可选（PostgreSQL/MongoDB） |

对于 10 人以内的小团队使用，完全足够！

---

## 🔧 自定义域名（可选）

如果您有自己的域名，可以在 Railway 中配置：
1. 进入项目设置
2. 选择 "Settings" → "Networking" → "Custom Domains"
3. 添加您的域名并配置 DNS

---

## ❓ 常见问题

**Q: 部署后显示 "Application Error"？**
A: 检查 Railway 日志，常见问题：
- 端口配置错误（ Railway 使用 `$PORT` 环境变量）
- 依赖安装失败（检查 requirements.txt）
- 启动命令错误

**Q: 如何更新代码？**
A: 只需推送到 GitHub，Railway 会自动检测并重新部署：
```bash
git add .
git commit -m "更新内容"
git push origin master
```

**Q: 如何停止计费？**
A: 在 Railway 面板中删除项目即可彻底停止。
