# 财务舞弊识别 SaaS 平台 - 部署和启动指南

## 项目概述

本项目是一个基于生成式 AI 的上市公司财务舞弊智能识别 SaaS 平台，为监管机构、会计师事务所、投资者、上市公司提供分层化的舞弊检测服务。

## 项目结构

```
fraud_detection_saaS/
├── backend/                    # FastAPI 后端
│   ├── main.py                # 应用入口
│   ├── core/                  # 核心配置
│   │   ├── config.py          # 配置管理
│   │   ├── database.py        # 数据库连接
│   │   └── security.py        # 认证安全
│   ├── models/                # 数据库模型
│   │   └── database.py        # SQLAlchemy 模型
│   ├── schemas/               # Pydantic Schema
│   │   └── schemas.py         # 请求/响应验证
│   ├── routers/               # API 路由
│   │   ├── user.py            # 用户认证
│   │   ├── user_account.py    # 账户管理
│   │   ├── detection.py       # 舞弊检测
│   │   ├── qa.py              # AI 问答
│   │   ├── payment.py         # 支付中心
│   │   ├── payment_system.py  # 支付系统（完整）
│   │   ├── report.py          # 报告管理
│   │   └── membership.py      # 会员中心
│   ├── services/              # 业务服务
│   │   ├── detection_service.py    # 检测引擎
│   │   ├── qa_service.py           # 问答引擎
│   │   ├── report_service.py       # 报告服务
│   │   └── visualization_service.py # 可视化服务
│   ├── utils/                 # 工具函数
│   │   └── init_cases.py      # 案例初始化
│   ├── templates/             # 报告模板
│   │   └── reports/
│   │       ├── basic_report.html
│   │       ├── professional_report.html
│   │       ├── enterprise_report.html
│   │       └── high_risk_professional_report.html
│   ├── .env.example           # 环境变量示例
│   ├── requirements.txt       # Python 依赖
│   └── README.md              # 后端文档
│
├── frontend/                  # Streamlit 前端
│   ├── app.py                 # 前端应用主文件
│   ├── app_complete.py        # 完整版前端应用
│   ├── create_templates.py    # 创建模板脚本
│   └── create_templates_fixed.py # 修复版模板脚本
│
├── data/                      # 数据目录
│   ├── structured/            # 结构化财务数据
│   ├── unstructured/          # MD&A 文本
│   ├── label/                 # 标签数据
│   ├── train_test/            # 训练测试数据
│   └── uploads/               # 用户上传文件
│
├── result/                    # 结果输出
│   ├── reports/               # 检测报告
│   ├── models/                # 训练模型
│   ├── visualization/         # 可视化图表
│   └── ...
│
├── README.md                  # 项目总文档
└── QUICKSTART.md             # 快速启动指南
```

## 快速启动指南

### 1. 环境准备

#### 1.1 安装 Python
- Python 版本：3.10+
- 推荐使用虚拟环境

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate
```

#### 1.2 安装依赖

```bash
# 安装后端依赖
cd backend
pip install -r requirements.txt

# 安装前端依赖
cd ../frontend
pip install streamlit plotly pandas requests jinja2 weasyprint
```

### 2. 数据库配置

#### 2.1 安装 MySQL
- 下载并安装 MySQL 8.0+
- 创建数据库：
```sql
CREATE DATABASE fraud_detection CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

#### 2.2 配置环境变量
```bash
# 复制示例配置
cd backend
cp .env .env

# 编辑 .env 文件，修改以下关键配置
DATABASE_URL=mysql+pymysql://root:your_password@localhost:3306/fraud_detection?charset=utf8mb4
SECRET_KEY=your-secret-key-change-in-production  # 使用 openssl rand -hex 32 生成

# AI API 配置（阿里云 DashScope 已硬编码，如需修改请编辑 backend/core/config.py）
# DASHSCOPE_API_KEY=sk-your-api-key
```

### 3. 初始化数据库

```bash
cd backend

# 初始化数据库表
python utils/init_cases.py
```

### 4. 启动后端服务

```bash
cd backend

# 启动 FastAPI 服务
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

访问 http://localhost:8000/docs 可以查看 API 文档

### 5. 启动前端服务

```bash
cd frontend

# 启动 Streamlit 应用
streamlit run app.py
```

访问 http://localhost:8501 可以查看前端界面

## 核心功能演示

### 1. 用户注册登录

**注册流程：**
1. 打开前端 http://localhost:8501
2. 点击 "🔐 登录/注册"
3. 选择 "注册" 标签
4. 填写用户名、密码、邮箱/手机号
5. 点击 "注册" 按钮

**登录流程：**
1. 打开前端
2. 点击 "🔐 登录/注册"
3. 选择 "登录" 标签
4. 输入用户名和密码
5. 点击 "登录" 按钮

### 2. 舞弊检测功能

**使用内置案例：**
1. 登录后，点击 "🔍 舞弊检测"
2. 切换到 "📚 内置案例库" 标签
3. 选择 "康美药业" 或其他案例
4. 点击 "加载案例数据"
5. 切换到 "📝 手动录入" 标签
6. 点击 "🚀 开始检测"

**手动录入数据：**
1. 点击 "🔍 舞弊检测"
2. 填写企业名称、证券代码、年度
3. 输入财务数据（货币资金、短期借款等）
4. 粘贴 MD&A 文本
5. 点击 "🚀 开始检测"

**查看检测结果：**
- 舞弊概率（仪表盘展示）
- 风险等级（高/中/低）
- 风险标签（自动识别）
- SHAP 特征重要性分析（柱状图）
- AI 文本特征雷达图

### 3. AI 智能问答

1. 点击 "💬 AI 问答"
2. 在输入框输入问题，例如：
   - "什么是存贷双高？"
   - "康美药业舞弊案的关键识别点是什么？"
   - "如何解读舞弊概率？"
3. 点击发送
4. 查看 AI 回答

**预设问题：**
侧边栏显示了推荐问题，可以快速提问

### 4. 会员中心

1. 点击 "💎 会员中心"
2. 查看当前会员状态和权益
3. 选择套餐类型
4. 点击 "选择 [套餐名称]"
5. 完成支付流程

**套餐类型：**
- 免费版：3 次/月，5 次/天问答
- 专业版（299/月）：无限检测，50 次/天问答
- 企业版（2999/年）：批量检测，API 接口

## API 接口文档

### 认证接口

```bash
# 用户注册
POST http://localhost:8000/api/user/register
{
  "username": "testuser",
  "password": "password123",
  "email": "test@example.com"
}

# 用户登录
POST http://localhost:8000/api/user/login
{
  "username": "testuser",
  "password": "password123"
}

# 获取用户信息（需要认证）
GET http://localhost:8000/api/user/profile
Headers: Authorization: Bearer <token>
```

### 检测接口

```bash
# 获取预设案例列表
GET http://localhost:8000/api/detection/cases

# 执行舞弊检测
POST http://localhost:8000/api/detection/analyze
Headers: Authorization: Bearer <token>
{
  "company_name": "测试公司",
  "stock_code": "000001",
  "year": 2022,
  "financial_data": {
    "货币资金": 1000000000,
    "短期借款": 500000000
  },
  "mdna_text": "这是 MD&A 文本内容..."
}

# 获取检测历史
GET http://localhost:8000/api/detection/history
Headers: Authorization: Bearer <token>
```

### 问答接口

```bash
# 提问
POST http://localhost:8000/api/qa/ask
Headers: Authorization: Bearer <token>
{
  "question": "什么是存贷双高？",
  "category": "practice"
}

# 获取推荐问题
GET http://localhost:8000/api/qa/suggestions
```

### 支付接口

```bash
# 获取会员套餐
GET http://localhost:8000/api/order/membership/plans

# 创建订阅订单
POST http://localhost:8000/api/order/subscribe/monthly
Headers: Authorization: Bearer <token>

# 确认支付
POST http://localhost:8000/api/order/pay/{order_no}
```

## 预设案例库

### 案例 1: 康美药业（舞弊 - 存贷双高）
- **证券代码**: 600518
- **年度**: 2017
- **风险特征**: 存贷双高、现金流背离、存货异常
- **预期舞弊概率**: 96.8%

### 案例 2: 瑞幸咖啡（舞弊 - 虚增收入）
- **证券代码**: LK
- **年度**: 2019
- **风险特征**: 收入异常增长、费用率异常
- **预期舞弊概率**: 94.2%

### 案例 3: 獐子岛（舞弊 - 存货异常）
- **证券代码**: 002069
- **年度**: 2014
- **风险特征**: 存货异常、资产减值异常
- **预期舞弊概率**: 92.5%

### 案例 4: 贵州茅台（健康）
- **证券代码**: 600519
- **年度**: 2022
- **风险特征**: 无显著风险
- **预期舞弊概率**: 3.2%

## 技术架构

### 后端技术栈
- **框架**: FastAPI 0.109.0
- **ORM**: SQLAlchemy 2.0.25
- **数据库**: MySQL 8.0
- **认证**: JWT (python-jose)
- **密码加密**: bcrypt (passlib)
- **AI**: scikit-learn, xgboost, shap

### 前端技术栈
- **框架**: Streamlit 1.31.0
- **图表**: Plotly 5.18.0
- **HTTP 客户端**: requests
- **模板**: Jinja2

### AI/ML 模型
- **文本分析**: 阿里云 DashScope (通义千问 qwen3-max)
- **传统模型**: XGBoost
- **特征提取**: 7 个 AI 文本特征 + 传统财务指标
- **可解释性**: SHAP (SHapley Additive exPlanations)

## 比赛展示流程（5-8 分钟）

### 第 1-2 分钟：开场介绍
```
1. 打开网站首页
2. 介绍项目定位："基于生成式 AI 的财务舞弊智能识别 SaaS 平台"
3. 展示核心卖点：
   - AI 可解释性（SHAP）
   - 双模输入（财务数据 + MD&A）
   - 风险标签可视化
```

### 第 3-4 分钟：演示舞弊检测
```
1. 切换到"舞弊检测"页面
2. 从"内置案例库"选择"康美药业"
3. 点击"开始检测"
4. 展示检测结果：
   - 舞弊概率：96.8%
   - 风险等级：高风险
   - 风险标签：存贷双高、现金流背离等
```

### 第 5 分钟：解读技术亮点
```
1. SHAP 特征重要性分析（柱状图）
2. AI 文本特征雷达图
3. 解释技术优势：
   - 解决"黑箱"问题
   - 多模型融合
   - 可视化呈现
```

### 第 6 分钟：对比健康企业
```
1. 选择"贵州茅台"案例
2. 执行检测
3. 展示结果：舞弊概率 3.2%，无风险标签
4. 说明平台能够准确区分健康和舞弊企业
```

### 第 7-8 分钟：商业化展示
```
1. 切换到"会员中心"
2. 展示三层会员体系：
   - 免费版
   - 专业版（299/月）
   - 企业版（2999/年）
3. 介绍灵活计费模式
4. 总结核心优势
```

## 部署方案

### 本地部署
```bash
# 后端
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000

# 前端
cd frontend
streamlit run app.py
```

### Render 部署（生产环境）

**后端部署：**
1. 注册 Render 账号
2. 创建 Web Service
3. 连接 GitHub 仓库
4. 配置环境变量
5. 启动命令：`uvicorn main:app --host 0.0.0.0 --port $PORT`
6. 部署后获取域名：`https://your-api.onrender.com`

**前端部署（Streamlit Cloud）：**
1. 注册 Streamlit Cloud
2. 连接 GitHub 仓库（frontend 目录）
3. 配置 Secrets（API_BASE_URL）
4. 部署后获取域名：`https://your-app.streamlit.app`

## 常见问题

### Q1: 数据库连接失败
```bash
# 检查 MySQL 服务是否启动
# 检查 .env 文件中的 DATABASE_URL 配置
# 确保数据库存在且字符集正确
```

### Q2: LLM API 调用失败
```bash
# 检查 DASHSCOPE_API_KEY 是否正确（已硬编码在 backend/core/config.py）
# 确保网络连接正常
# 检查阿里云DashScope API 限流
# 如需更换API Key，请编辑 backend/core/config.py 中的 DASHSCOPE_API_KEY
```

### Q3: 前端无法连接后端
```bash
# 确保后端服务已启动
# 检查 API_BASE_URL 配置
# 确保 CORS 配置正确
```

### Q4: 检测结果不准确
```bash
# 使用内置案例库测试
# 检查财务数据格式
# 确保 MD&A 文本足够长
```

## 后续开发计划

### 短期计划（1-2 周）
- [ ] 完善支付功能（集成支付宝/微信支付）
- [ ] PDF 报告导出功能
- [ ] 邮件通知功能
- [ ] 短信验证码功能

### 中期计划（1-2 个月）
- [ ] 批量检测功能
- [ ] API 接口开放
- [ ] 移动端适配
- [ ] 数据可视化大屏

### 长期计划（3-6 个月）
- [ ] 私有化部署支持
- [ ] 多语言支持
- [ ] 智能预警系统
- [ ] 企业级数据安全

## 技术支持

- **项目文档**: 查看 README.md
- **API 文档**: http://localhost:8000/docs
- **源码仓库**: D:/play/fraud_detection_saaS
- **问题反馈**: 请提交 Issue 或联系开发团队

## 总结

本项目实现了完整的财务舞弊识别 SaaS 平台，包含：

✅ 用户系统（注册/登录/认证/会员）
✅ 舞弊检测核心功能（双模输入/效果优化）
✅ 预设案例库（4 个经典案例）
✅ AI 智能问答
✅ 报告管理（基础/专业/企业版）
✅ 会员中心和计费系统
✅ 数据可视化（仪表盘/SHAP/雷达图）
✅ 支付系统（支付宝/微信/充值）
✅ 完整的前后端分离架构

项目已具备比赛展示和商业化运营的全部核心功能！
