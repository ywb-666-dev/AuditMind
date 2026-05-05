# Koyeb 部署指南

## 一、后端部署 (FastAPI)

### 1. 准备数据库
Koyeb 提供免费 PostgreSQL 数据库（推荐）：
- 登录 https://app.koyeb.com
- 点击 "Database" → "Create Database"
- 选择 PostgreSQL，记录连接字符串

或者继续使用你的 MySQL 数据库（确保允许外网访问）

### 2. 部署后端服务

#### 方法一：使用 GitHub 自动部署（推荐）
1. 登录 https://app.koyeb.com
2. 点击 "Create Service"
3. 选择 "GitHub" 作为部署源
4. 授权并选择你的仓库 `ywb-666-dev/AuditMind`
5. 配置：
   - **Builder**: Dockerfile
   - **Dockerfile location**: `./backend/Dockerfile`
   - **Subdirectory**: `backend/`
6. 添加环境变量（Environment Variables）：

```bash
# 数据库（使用Koyeb PostgreSQL或你自己的MySQL）
DATABASE_URL=postgresql://user:pass@host:5432/dbname
# 或者 MySQL
# DATABASE_URL=mysql+pymysql://user:pass@host:3306/dbname

# 安全配置（生成随机字符串）
SECRET_KEY=your-random-secret-key-here-min-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080

# AI API配置
DASHSCOPE_API_KEY=sk-your-dashscope-api-key
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
MODEL_QWEN=deepseek-v3.2

# 应用配置
APP_NAME=AuditMind-财务舞弊识别平台
APP_VERSION=1.0.0
DEBUG=False
API_PREFIX=/api

# 额度限制（生产环境设为false）
BYPASS_DETECTION_QUOTA=False

# 免费版额度
FREE_USER_DAILY_AI_QUESTIONS=5
FREE_USER_MONTHLY_DETECTIONS=3
```

7. 点击 "Deploy"

#### 方法二：使用 Docker 镜像
```bash
# 本地构建并推送（可选）
cd backend
docker build -t your-dockerhub-username/auditmind-backend .
docker push your-dockerhub-username/auditmind-backend
```

然后在 Koyeb 选择 "Docker Hub" 作为部署源。

### 3. 获取后端地址
部署完成后，Koyeb 会分配一个域名如：
`https://fraud-detection-backend-yourname.koyeb.app`

## 二、前端部署 (Streamlit Cloud)

### 1. 更新前端 API 地址
修改 `frontend/app.py` 中的 API_BASE_URL：

```python
# 第20行左右
API_BASE_URL = "https://你的koyeb后端地址.koyeb.app/api"
```

### 2. 推送到 GitHub
```bash
git add .
git commit -m "Update for Koyeb deployment"
git push origin master
```

### 3. Streamlit Cloud 部署
1. 访问 https://streamlit.io/cloud
2. 点击 "New app"
3. 选择你的 GitHub 仓库
4. 配置：
   - **Main file path**: `frontend/app.py`
   - **Python version**: 3.11
5. 点击 "Deploy"

### 4. 添加 Secrets（重要）
在 Streamlit Cloud 应用设置中添加：
```toml
API_BASE_URL = "https://你的koyeb后端地址.koyeb.app/api"
```

## 三、需要修改的文件清单

### 后端（已完成）
- ✅ `backend/Dockerfile` - 已创建
- ✅ `backend/.dockerignore` - 已创建
- ✅ `backend/requirements.txt` - 已存在

### 前端（需要更新）
需要修改 `frontend/app.py` 中的 API 地址：

```python
# 找到这一行（约第20行）
# API_BASE_URL = "http://localhost:8000/api"

# 改为你的 Koyeb 后端地址
API_BASE_URL = "https://fraud-detection-backend-yourname.koyeb.app/api"
```

## 四、Koyeb vs Render 主要区别

| 特性 | Render | Koyeb |
|------|--------|-------|
| 免费数据库 | PostgreSQL | PostgreSQL |
| 需要绑卡 | 是 | **否** |
| 自动休眠 | 15分钟 | **无（持续运行）** |
| 免费额度 | 750小时/月 | **每月$5等值额度** |
| 部署方式 | Docker/Native | **Docker推荐** |
| 自定义域名 | 支持 | 支持 |

## 五、常见问题

### 1. 数据库连接失败
确保数据库允许外网访问，或直接使用 Koyeb 托管 PostgreSQL。

### 2. 模型文件太大
如果模型文件（.pkl）太大导致构建慢，可以：
- 使用 Koyeb 的 Volume 挂载
- 或将模型上传到 S3/阿里云OSS，启动时下载

### 3. 内存不足
Koyeb 免费版有内存限制，如果模型加载失败：
- 在 `koyeb.yaml` 中设置更大的实例类型
- 或只加载必要的模型

## 六、完整部署命令

```bash
# 1. 确保模型文件已复制
cp D:/play/models/*.pkl backend/result/models/

# 2. 更新前端API地址
# （手动修改 frontend/app.py 中的 API_BASE_URL）

# 3. 提交并推送
git add .
git commit -m "Ready for Koyeb deployment"
git push origin master

# 4. 在 Koyeb 控制台部署后端
# 5. 获取后端地址并更新前端
# 6. 在 Streamlit Cloud 部署前端
```

## 七、验证部署

后端部署成功后访问：
- API文档: `https://your-app.koyeb.app/docs`
- 健康检查: `https://your-app.koyeb.app/`

前端部署成功后：
- 测试登录功能
- 测试文件上传
- 测试检测功能
