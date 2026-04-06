# 财务舞弊识别 SaaS 平台

基于生成式 AI 的上市公司财务舞弊智能识别 SaaS 平台。

## 项目结构

```
fraud_detection_saaS/
├── backend/                 # FastAPI 后端
│   ├── main.py             # 应用入口
│   ├── core/               # 核心配置
│   │   ├── config.py       # 配置管理
│   │   ├── database.py     # 数据库连接
│   │   └── security.py     # 认证安全
│   ├── models/             # 数据库模型
│   │   └── database.py     # SQLAlchemy 模型
│   ├── schemas/            # Pydantic Schema
│   │   └── schemas.py      # 请求/响应验证
│   ├── routers/            # API 路由
│   │   ├── user.py         # 用户认证
│   │   ├── detection.py    # 舞弊检测
│   │   ├── qa.py           # AI 问答
│   │   ├── payment.py      # 支付中心
│   │   └── report.py       # 报告管理
│   └── utils/              # 工具函数
│       └── init_cases.py   # 案例初始化
│
├── frontend/               # Streamlit 前端
│   └── app.py             # 前端应用
│
├── data/                   # 数据目录
│   ├── structured/        # 结构化财务数据
│   ├── unstructured/      # MD&A 文本
│   └── uploads/           # 上传文件
│
└── result/                 # 结果输出
    ├── reports/           # 检测报告
    └── models/            # 模型文件
```

## 快速开始（PyCharm + 本机环境 - 最简单）

**无需虚拟环境，直接使用本机 Python！**

### 5分钟快速启动

1. **PyCharm 打开项目**
   - `File` → `Open` → 选择 `fraud_detection_saaS` 文件夹

2. **配置本机 Python**
   - `File` → `Settings` → `Python Interpreter`
   - 选择本机 Python 3.10+（或点击 `Add Interpreter` → `System Interpreter`）

3. **安装依赖**（PyCharm Terminal 中执行）
```bash
pip install -r backend/requirements.txt
pip install streamlit plotly pandas requests
```

4. **配置环境变量**
```bash
cd backend
copy .env .env
# .env 已配置为你的 MySQL：root:712693@localhost:3306
```

> > **重要**：首次使用前需要创建数据库：
> > ```sql
> > CREATE DATABASE fraud_detection CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
> > ```

5. **复制模型文件**
```bash
xcopy D:\play\models\*.pkl backend\result\models\ /Y
```

6. **初始化数据库**
```bash
cd backend
python utils/init_cases.py
```

7. **启动运行**
   - **最简单方式**：双击 `start.bat`，选择 `3. 启动前后端`
   - **或 PyCharm 配置**：查看 [PYCHARM_GUIDE.md](PYCHARM_GUIDE.md) 获取详细配置说明

8. **访问**
   - 后端 API：http://localhost:8000/docs
   - 前端界面：http://localhost:8501

---

## 传统命令行方式

### 1. 环境准备

```bash
# 创建虚拟环境
python -m venv venv
cd venv
Scripts/activate  # Windows
# source bin/activate  # Linux/Mac

# 安装依赖
pip install -r backend/requirements.txt
```

### 2. 配置数据库

```bash
# 启动 MySQL 服务
# 创建数据库
CREATE DATABASE fraud_detection CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

# 修改配置文件
cp backend/.env backend/.env
# 编辑.env 文件，填入数据库连接信息
```

### 3. 启动后端

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

访问 http://localhost:8000/docs 查看 API 文档

### 4. 初始化案例数据

```bash
cd backend
python utils/init_cases.py
```

### 5. 启动前端

```bash
cd frontend
streamlit run app.py
```

访问 http://localhost:8501 查看前端界面

## 核心功能

### 用户系统
- 注册/登录/认证
- 会员等级管理（免费版/专业版/企业版）
- 检测额度控制

### 舞弊检测
- 双模输入：结构化财务数据 + MD&A 文本
- AI 特征提取：7 个文本风险特征
- SHAP 可解释性分析
- 风险标签可视化

### AI 问答
- 财务舞弊理论知识
- 实操指导
- 案例解析
- 平台使用帮助

### 支付系统
- 支付宝/微信支付
- 会员订阅（月度/季度/年度）
- 单次检测购买
- 账户充值

## 预设案例库

| 案例 | 类型 | 风险特征 |
|------|------|----------|
| 康美药业 | 舞弊 | 存贷双高、现金流背离 |
| 瑞幸咖啡 | 舞弊 | 收入虚增、费用率异常 |
| 獐子岛 | 舞弊 | 存货异常、资产减值 |
| 贵州茅台 | 健康 | 财务状况健康 |

## API 接口

### 用户认证
- `POST /api/user/register` - 用户注册
- `POST /api/user/login` - 用户登录
- `GET /api/user/profile` - 获取个人信息

### 舞弊检测
- `GET /api/detection/cases` - 获取预设案例
- `POST /api/detection/analyze` - 执行检测
- `GET /api/detection/history` - 检测历史

### AI 问答
- `POST /api/qa/ask` - 提问
- `GET /api/qa/suggestions` - 推荐问题

### 支付中心
- `GET /api/order/membership/plans` - 会员套餐
- `POST /api/order/create` - 创建订单
- `POST /api/order/pay/{order_no}` - 确认支付

## 技术栈

- **后端**: FastAPI + SQLAlchemy + MySQL
- **前端**: Streamlit + Plotly
- **AI**: 阿里云 DashScope (通义千问 qwen3-max)
- **认证**: JWT + bcrypt

## 部署方案

### Render 部署

1. 后端：Render Web Service
2. 数据库：Render MySQL
3. 前端：Streamlit Community Cloud

### 本地部署

```bash
# 后端
uvicorn main:app --host 0.0.0.0 --port 8000

# 前端
streamlit run app.py
```

## 开发计划

- [ ] 批量检测功能
- [ ] PDF 报告导出
- [ ] API 接口开放
- [ ] 数据可视化大屏
- [ ] 移动端适配

## License

MIT License
