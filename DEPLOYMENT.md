# 财务舞弊识别 SaaS 平台 - 部署指南

## 一、本地开发环境启动

### 1. 前置要求
- Python 3.10+
- MySQL 8.0+ (或 SQLite 用于开发测试)
- SiliconFlow API Key (用于AI分析)

### 2. 快速启动

```bash
# 方式1：使用启动脚本（Windows）
start.bat

# 方式2：手动启动
# 1. 安装依赖
cd backend
pip install -r requirements.txt

# 2. 配置环境变量
cp .env .env
# 编辑 .env 填入数据库和API密钥

# 3. 初始化数据库
python utils/init_cases.py

# 4. 启动后端
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 5. 另开终端启动前端
cd ../frontend
pip install streamlit plotly pandas requests
streamlit run app.py
```

### 3. 访问地址
- 前端界面: http://localhost:8501
- 后端API: http://localhost:8000
- API文档: http://localhost:8000/docs

---

## 二、生产环境部署

### 2.1 后端部署（Render）

#### 步骤1：准备代码
```bash
# 确保代码已推送到 GitHub
git add .
git commit -m "Prepare for production deployment"
git push origin main
```

#### 步骤2：Render 配置
1. 登录 [Render](https://render.com)
2. 点击 "New +" → "Web Service"
3. 连接 GitHub 仓库
4. 配置如下：
   - **Name**: fraud-detection-api
   - **Root Directory**: backend
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

#### 步骤3：环境变量配置
在 Render Dashboard 的 Environment 中添加：
```
DATABASE_URL=postgresql://user:pass@host:5432/fraud_detection
SECRET_KEY=your-random-secret-key-at-least-32-chars
SILICONFLOW_API_KEY=your-siliconflow-api-key
APP_NAME=慧审 - 财务舞弊识别平台
DEBUG=False
```

#### 步骤4：数据库设置
1. 在 Render 创建 PostgreSQL 数据库
2. 复制连接字符串到 `DATABASE_URL`
3. 在 Shell 中运行：`python utils/init_cases.py`

---

### 2.2 前端部署（Streamlit Cloud）

#### 步骤1：准备代码
```bash
# 确保 frontend/app.py 中的 API_BASE_URL 指向 Render 后端
API_BASE_URL = "https://fraud-detection-api.onrender.com/api"
```

#### 步骤2：部署到 Streamlit Cloud
1. 登录 [Streamlit Cloud](https://streamlit.io/cloud)
2. 点击 "New App"
3. 选择 GitHub 仓库
4. 配置：
   - **File path**: `frontend/app.py`
   - **Python version**: 3.10

#### 步骤3：配置 Secrets
在 Streamlit Cloud 的 Secrets 中添加：
```toml
API_BASE_URL = "https://fraud-detection-api.onrender.com/api"
```

---

## 三、配置文件说明

### 3.1 后端 .env 配置

```bash
# 应用配置
APP_NAME=慧审 - 财务舞弊识别平台
APP_VERSION=1.0.0
DEBUG=False
API_PREFIX=/api

# 数据库配置（MySQL）
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/fraud_detection?charset=utf8mb4

# 数据库配置（PostgreSQL - Render）
# DATABASE_URL=postgresql://user:pass@host:5432/fraud_detection

# 安全配置
SECRET_KEY=your-secret-key-change-in-production-min-32-characters
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080  # 7天

# LLM API 配置（阿里云 DashScope - 通义千问）
# 已硬编码在代码中，如需修改请编辑 backend/core/config.py
# DASHSCOPE_API_KEY=sk-your-api-key
# DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
# MODEL_QWEN=qwen3-max
```

### 3.2 前端配置

在 `frontend/app.py` 中修改：
```python
# 开发环境
API_BASE_URL = "http://localhost:8000/api"

# 生产环境（部署后）
# API_BASE_URL = "https://your-api.onrender.com/api"
```

---

## 四、模型文件准备

确保以下模型文件存在于正确位置：

```
backend/result/models/
├── model_ai_XGBoost.pkl       # AI文本特征模型
├── model_trad_XGBoost.pkl     # 传统财务指标模型
├── scaler.pkl                 # 数据标准化器
├── selected_features.pkl      # 选择的特征列表
└── numeric_columns.pkl        # 数值列定义
```

### 从训练目录复制模型
```bash
# Windows
copy D:\play\models\*.pkl backend\result\models\

# Linux/Mac
cp /path/to/models/*.pkl backend/result/models/
```

---

## 五、关键功能验证

### 5.1 用户注册/登录
1. 访问前端页面
2. 点击登录/注册
3. 测试注册新用户
4. 测试登录已有用户

### 5.2 舞弊检测（AI分析）
1. 登录后进入"舞弊检测"
2. 选择"内置案例库"→"康美药业"
3. 点击"加载案例数据"
4. 点击"开始检测"
5. 验证：
   - 舞弊概率应在 80%+（高风险）
   - 风险标签应包含"存贷双高"、"现金流背离"
   - AI特征雷达图应有明显峰值

### 5.3 AI问答
1. 进入"AI问答"页面
2. 输入问题："什么是存贷双高？"
3. 验证能收到专业回答

---

## 六、故障排查

### 问题1：后端无法启动
```bash
# 检查依赖
pip install -r requirements.txt

# 检查端口占用
lsof -i :8000  # Linux/Mac
netstat -ano | findstr :8000  # Windows

# 检查模型文件是否存在
ls backend/result/models/
```

### 问题2：AI分析无响应
- 检查 `SILICONFLOW_API_KEY` 是否正确
- 检查网络连接
- 查看后端日志中的错误信息

### 问题3：前端无法连接后端
- 检查 `API_BASE_URL` 配置
- 检查后端CORS配置（已配置允许streamlit.app域名）
- 检查后端是否正常运行

### 问题4：数据库连接失败
- 检查 `DATABASE_URL` 格式
- 确保数据库已创建且字符集为 utf8mb4
- 检查数据库用户权限

---

## 七、性能优化建议

### 7.1 后端优化
- 启用 Gzip 压缩
- 使用 Redis 缓存 AI 分析结果（相同文本可复用）
- 数据库连接池配置

### 7.2 AI调用优化
- LLM API 结果缓存（24小时）
- 异步批量处理
- 降级策略（API失败时使用规则-based分析）

---

## 八、安全建议

1. **生产环境必须使用 HTTPS**
2. **SECRET_KEY** 使用随机生成的强密钥（`openssl rand -hex 32`）
3. **数据库密码** 使用强密码
4. **API密钥** 不要提交到代码仓库
5. **定期备份** 数据库

---

## 九、联系支持

如有问题，请查看：
- API文档：`/docs` 端点
- 项目文档：README.md
- 代码仓库：GitHub Issues
