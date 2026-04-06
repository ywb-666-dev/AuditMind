# Vercel 部署指南

## ⚠️ 重要提示

Vercel 是** Serverless 平台**，有以下限制：
- **函数大小限制**: 50MB（压缩后）
- **冷启动**: 长时间未访问后会进入休眠
- **模型文件**: 如果模型文件太大，需要外部存储
- **执行时间**: 免费版最大 10秒/请求（Hobby版）

**推荐**: 如果你的模型文件较大（>30MB），建议使用 **Railway** 或 **Koyeb** 替代 Vercel。

## 一、检查模型文件大小

```bash
# 检查模型文件总大小
cd backend/result/models
du -sh .
```

- 如果 < 30MB: 可以继续 Vercel 部署
- 如果 > 30MB: 建议使用 Railway/Koyeb/Render

## 二、需要修改的地方

### 1. 前端 API 地址（硬编码）
修改 `frontend/app.py` 第28行：

```python
# Vercel部署后的地址
API_BASE_URL = "https://你的vercel域名.vercel.app/api"
```

### 2. 数据库配置
Vercel 需要**外部数据库**，推荐：
- **Neon** (PostgreSQL，免费): https://neon.tech
- **PlanetScale** (MySQL，免费): https://planetscale.com
- **Supabase** (PostgreSQL，免费): https://supabase.com

### 3. 模型文件处理（如果太大）

#### 方案A：模型文件 < 30MB（直接部署）
模型文件会随代码一起部署，无需修改。

#### 方案B：模型文件 > 30MB（外部存储）
需要将模型上传到外部存储（如 AWS S3、阿里云 OSS），启动时下载：

```python
# 在 detection_service.py 中添加下载逻辑
import os
import requests

MODEL_DIR = "/tmp/models"  # Vercel 只有 /tmp 可写

def download_models():
    models = [
        "model_ai_XGBoost.pkl",
        "model_trad_XGBoost.pkl",
        "scaler.pkl"
    ]
    os.makedirs(MODEL_DIR, exist_ok=True)
    
    for model in models:
        url = f"https://你的存储桶.com/models/{model}"
        path = os.path.join(MODEL_DIR, model)
        if not os.path.exists(path):
            response = requests.get(url)
            with open(path, "wb") as f:
                f.write(response.content)
```

## 三、部署步骤

### 步骤1：准备数据库
1. 注册 Neon/PlanetScale/Supabase
2. 创建数据库，记录连接字符串
3. 执行 SQL 创建表结构（可以用原来的 MySQL 结构）

### 步骤2：安装 Vercel CLI
```bash
npm i -g vercel
```

### 步骤3：配置环境变量
在项目根目录创建 `.env` 文件：

```bash
# 数据库（使用 Neon PostgreSQL）
DATABASE_URL=postgresql://user:password@host.neon.tech/dbname

# 安全密钥
SECRET_KEY=your-random-secret-key-min-32-characters
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080

# AI API
DASHSCOPE_API_KEY=sk-your-dashscope-api-key
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
MODEL_QWEN=deepseek-v3.2

# 应用配置
APP_NAME=AuditMind
APP_VERSION=1.0.0
DEBUG=False
API_PREFIX=/api

# 额度配置
BYPASS_DETECTION_QUOTA=False
FREE_USER_DAILY_AI_QUESTIONS=5
FREE_USER_MONTHLY_DETECTIONS=3
```

### 步骤4：修改数据库驱动（PostgreSQL）
如果使用 Neon PostgreSQL，需要更新依赖：

```bash
# 添加到 backend/requirements.txt
psycopg2-binary==2.9.9
# 或
asyncpg==0.29.0
```

并修改 `backend/core/database.py` 中的数据库连接。

### 步骤5：部署
```bash
cd backend

# 登录 Vercel
vercel login

# 部署
vercel --prod

# 或链接到已有项目
vercel link
vercel --prod
```

## 四、目录结构要求

Vercel 需要特定的目录结构：

```
backend/
├── api/
│   └── index.py          # Serverless入口
├── vercel.json           # Vercel配置
├── main.py               # FastAPI主应用
├── requirements.txt      # 依赖
└── ...
```

## 五、常见问题

### 1. 函数大小超过 50MB
**错误**: `Error: The Serverless Function "api/index" is xx.xxx mb which exceeds the maximum size limit of 50 MB`

**解决**:
- 使用外部存储存放模型文件
- 或使用 Railway/Koyeb 替代

### 2. 数据库连接失败
Vercel 是 Serverless，数据库连接需要特殊处理：

```python
# 使用连接池或 PgBouncer
DATABASE_URL=postgresql://user:pass@host.neon.tech/dbname?pgbouncer=true
```

### 3. 冷启动慢
Vercel 长时间未访问后会休眠，首次请求较慢。

**解决**: 使用 Vercel 的 Cron Job 定期唤醒，或升级到 Pro 版。

### 4. 模型文件找不到
Vercel 只能写入 `/tmp` 目录：

```python
# 修改 config.py
UPLOAD_FOLDER = "/tmp/uploads"
REPORT_DIR = "/tmp/reports"
```

## 六、Vercel vs 其他平台对比

| 特性 | Vercel | Railway | Koyeb | Render |
|------|--------|---------|-------|--------|
| 免费额度 | 100GB流量 | $5/月 | $5/月 | 750小时 |
| 需要绑卡 | ❌ | ❌ | ❌ | ✅ |
| 持续运行 | ❌（冷启动）| ✅ | ✅ | ✅（有休眠）|
| 函数大小 | 50MB | 无限制 | 无限制 | 无限制 |
| 数据库 | 需外部 | 内置 | 需外部 | 内置 |
| 适合场景 | 小型项目 | 中大型 | 中大型 | 中大型 |

## 七、推荐方案

### 如果你坚持用 Vercel：
1. 使用 Neon 免费 PostgreSQL 数据库
2. 将模型文件放在 GitHub Release/云存储，启动时下载
3. 定期访问保持热启动（可用 UptimeRobot 免费监控）

### 如果模型文件 > 30MB：
**强烈建议**使用 **Railway** 或 **Koyeb**：
- 无需绑卡
- 无函数大小限制
- 持续运行无冷启动

## 八、部署验证

部署成功后访问：
```
https://你的项目.vercel.app/docs
```

检查：
- API 文档是否正常显示
- 数据库连接是否正常
- 模型加载是否成功
