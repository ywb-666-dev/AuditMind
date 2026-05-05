# PyCharm 运行指南 - 财务舞弊识别 SaaS 平台

## 快速开始（本机环境 - 最简单方式）

不想配置虚拟环境？直接用本机 Python！

### 5分钟快速启动

1. **PyCharm 打开项目**
   - `File` → `Open` → 选择 `D:\play\fraud_detection_saaS`

2. **配置本机 Python**
   - `File` → `Settings` → `Python Interpreter`
   - 选择本机 Python 3.10+（或点击 `Add Interpreter` → `System Interpreter`）

3. **安装依赖**（Terminal 中执行）
```bash
pip install -r backend/requirements.txt
pip install streamlit plotly pandas requests
```

4. **配置环境**
```bash
cd backend
copy .env .env
# .env 已配置为你的 MySQL
```

> > **重要**：首次使用前需要创建数据库：
> > ```sql
> > CREATE DATABASE fraud_detection CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
> > ```

5. **复制模型文件**
```bash
# 在 Terminal 中执行
xcopy D:\play\models\*.pkl backend\result\models\ /Y
```

6. **初始化数据库**
```bash
cd backend
python utils/init_cases.py
```

7. **运行项目**（两种方式）

   **方式 A - 使用 start.bat（最简单）**
   ```bash
   start.bat
   # 选择 3. 启动前后端
   ```

   **方式 B - PyCharm 运行配置**
   - 配置 Backend：`backend/main.py`，Working dir: `backend`
   - 配置 Frontend：Module: `streamlit`，Parameters: `run frontend/app.py`

8. **访问**
   - 后端：http://localhost:8000/docs
   - 前端：http://localhost:8501

---

## 一、项目结构（已清理）

```
fraud_detection_saaS/
├── backend/                    # FastAPI 后端
│   ├── core/                   # 核心配置
│   │   ├── config.py          # 配置管理（含DashScope API）
│   │   ├── database.py        # 数据库连接
│   │   └── security.py        # 认证安全
│   ├── models/                 # 数据库模型
│   │   └── database.py        # SQLAlchemy 模型
│   ├── routers/                # API 路由
│   │   ├── user.py            # 用户认证
│   │   ├── detection.py       # 舞弊检测
│   │   ├── qa.py              # AI 问答
│   │   └── ...
│   ├── services/               # 业务服务
│   │   ├── detection_service.py   # 检测引擎（调用qwen3-max）
│   │   └── qa_service.py          # 问答引擎
│   ├── utils/                  # 工具函数
│   │   └── init_cases.py      # 初始化案例
│   ├── templates/              # 报告模板
│   ├── main.py                 # 应用入口
│   ├── requirements.txt        # Python依赖
│   └── .env.example            # 环境变量示例
│
├── frontend/                   # Streamlit 前端
│   └── app.py                  # 主应用
│
├── data/                       # 数据目录
├── result/                     # 结果输出
│   └── models/                 # 训练好的模型文件
├── README.md                   # 项目说明
├── QUICKSTART.md              # 快速开始
└── start.bat                   # 启动脚本
```

## 二、PyCharm 配置步骤

### 步骤 1：打开项目

1. 打开 PyCharm
2. 选择 `File` → `Open`
3. 选择 `D:\play\fraud_detection_saaS` 文件夹
4. 点击 `OK`

### 步骤 2：配置 Python 解释器

#### 方式 A：使用本机 Python 环境（最简单）

**推荐！无需创建虚拟环境，直接使用本机 Python。**

1. 打开 `File` → `Settings`（或按 `Ctrl+Alt+S`）
2. 导航到 `Project: fraud_detection_saaS` → `Python Interpreter`
3. 在右侧选择已有的 Python 解释器（如 Python 3.10、3.11、3.12）
4. 如果没有显示，点击 `Add Interpreter` → `Add Local Interpreter`
5. 选择 `System Interpreter`，然后选择本机 Python 路径（如 `C:\Python312\python.exe`）
6. 点击 `OK`

#### 方式 B：使用 PyCharm 创建虚拟环境

1. 打开 `File` → `Settings`（或按 `Ctrl+Alt+S`）
2. 导航到 `Project: fraud_detection_saaS` → `Python Interpreter`
3. 点击齿轮图标 ⚙️ → `Add`
4. 选择 `Virtualenv Environment` → `New`
5. 配置：
   - **Location**: `D:\play\fraud_detection_saaS\venv`
   - **Base interpreter**: 选择 Python 3.10 或更高版本
6. 点击 `OK` 创建

#### 方式 C：使用已有虚拟环境

1. 同上打开设置
2. 点击齿轮图标 ⚙️ → `Add`
3. 选择 `Virtualenv Environment` → `Existing`
4. 选择已有的虚拟环境路径
5. 点击 `OK`

### 步骤 3：安装依赖

**使用本机环境直接安装（所有依赖会安装到本机 Python）**

打开 PyCharm 的 `Terminal`（底部工具栏或 `Alt+F12`），执行：

```bash
# 安装后端依赖
pip install -r backend/requirements.txt

# 安装前端依赖
pip install streamlit plotly pandas requests
```

> 💡 **提示**：如果提示 pip 需要升级，先执行 `python -m pip install --upgrade pip`

> ⚠️ **注意**：使用本机环境会全局安装这些包。如果担心冲突，建议使用虚拟环境。

### 步骤 4：配置环境变量

1. 复制环境变量示例文件：
```bash
cd backend
copy .env .env
```

2. 在 PyCharm 中打开 `backend/.env` 文件
3. 修改以下配置：

```env
# 数据库配置（已配置为你的MySQL）
DATABASE_URL=mysql+pymysql://root:712693@localhost:3306/fraud_detection?charset=utf8mb4

# 安全密钥（建议修改）
SECRET_KEY=your-random-secret-key-here-at-least-32-characters

# 其他配置保持默认即可
```

> 📝 **注意**：首次使用前需要先创建数据库：
> ```sql
> CREATE DATABASE fraud_detection CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
> ```

### 步骤 5：准备模型文件

确保模型文件已复制到正确位置：

```bash
# 在 PyCharm Terminal 中执行
# 从 D:\play\models 复制到项目目录
xcopy D:\play\models\*.pkl backend\result\models\ /Y
```

或手动复制：
- 源：`D:\play\models\*.pkl`
- 目标：`fraud_detection_saaS\backend\result\models\`

需要的模型文件：
- `model_ai_XGBoost.pkl`
- `model_trad_XGBoost.pkl`
- `scaler.pkl`
- `selected_features.pkl`
- `numeric_columns.pkl`

### 步骤 6：初始化数据库

在 PyCharm Terminal 中执行：
```bash
cd backend
python utils/init_cases.py
```

看到 `✅ 成功导入 4 个预设案例` 即表示成功。

## 三、运行项目

### 方式 1：使用 PyCharm 运行配置（推荐）

#### 配置后端运行

1. 点击右上角 `Add Configuration...`（或点击运行按钮旁的 ▼ → `Edit Configurations`）
2. 点击 `+` → `Python`
3. 配置：
   - **Name**: `Backend`
   - **Script path**: `backend/main.py`
   - **Working directory**: `D:\play\fraud_detection_saaS\backend`
   - **Python interpreter**: 选择你的本机 Python（如 Python 3.12）
4. 点击 `OK`
5. 点击运行按钮 ▶️ 或按 `Shift+F10`

后端将启动在：`http://localhost:8000`
API文档：`http://localhost:8000/docs`

#### 配置前端运行

1. 再次点击 `Add Configuration...`（或点击运行按钮旁的 ▼ → `Edit Configurations`）
2. 点击 `+` → `Python`
3. 配置：
   - **Name**: `Frontend`
   - **Module name**: `streamlit`（在输入框中手动输入）
   - **Parameters**: `run frontend/app.py`
   - **Working directory**: `D:\play\fraud_detection_saaS`
   - **Python interpreter**: 选择你的本机 Python（与后端相同）
4. 点击 `OK`
5. 点击运行按钮 ▶️

前端将启动在：`http://localhost:8501`

#### 同时运行前后端

1. 先运行 `Backend` 配置
2. 再运行 `Frontend` 配置
3. 两个服务会同时运行

### 方式 2：使用 start.bat

在 PyCharm Terminal 中执行：
```bash
start.bat
```
按提示选择启动模式。

### 方式 3：使用 PyCharm Terminal

开两个 Terminal 窗口：

**窗口 1 - 后端：**
```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**窗口 2 - 前端：**
```bash
cd frontend
streamlit run app.py
```

## 四、验证运行

### 1. 检查后端

浏览器访问：`http://localhost:8000/docs`
- 应看到 FastAPI 自动生成的 API 文档
- 表示后端正常运行

### 2. 检查前端

浏览器访问：`http://localhost:8501`
- 应看到 Streamlit 界面
- 表示前端正常运行

### 3. 测试检测功能

1. 在前端界面点击 "🔐 登录/注册"
2. 注册一个新用户
3. 进入 "🔍 舞弊检测"
4. 选择 "内置案例库" → "康美药业"
5. 点击 "加载案例数据"
6. 点击 "开始检测"
7. 应看到检测结果（舞弊概率、风险标签、SHAP分析等）

## 五、常见问题

### 问题 1：ModuleNotFoundError

**现象**：`ModuleNotFoundError: No module named 'xxx'`

**解决**：
```bash
# 在 PyCharm Terminal 中
pip install xxx
# 或
pip install -r backend/requirements.txt
```

### 问题 2：数据库连接失败

**现象**：`pymysql.err.OperationalError` 或 `Can't connect to MySQL server`

**解决**：
- 选项 A：安装并启动 MySQL
- 选项 B：改用 SQLite（修改 `.env` 中的 `DATABASE_URL`）

### 问题 3：模型文件找不到

**现象**：`⚠️ AI 模型文件不存在` 或检测失败

**解决**：
```bash
# 确保模型文件已复制
ls backend/result/models/
# 如果没有，执行复制
xcopy D:\play\models\*.pkl backend\result\models\ /Y
```

### 问题 4：DashScope API 调用失败

**现象**：`⚠️ LLM API调用失败`

**解决**：
1. 检查网络连接
2. 检查 `backend/core/config.py` 中的 `DASHSCOPE_API_KEY`
3. 阿里云 DashScope API 可能有调用限制，稍等重试

### 问题 5：前端无法连接后端

**现象**：前端显示 "请求失败" 或无法获取数据

**解决**：
1. 确保后端已启动（访问 `http://localhost:8000` 确认）
2. 检查 `frontend/app.py` 中的 `API_BASE_URL`
3. 检查后端日志是否有错误

## 六、PyCharm 调试技巧

### 后端调试

1. 在代码中设置断点（点击行号旁空白处）
2. 使用 `Debug` 模式运行（虫子图标 🐛 或 `Shift+F9`）
3. 当执行到断点时会暂停，可以查看变量值

常用断点位置：
- `backend/routers/detection.py` - 检测逻辑
- `backend/services/detection_service.py` - AI分析逻辑
- `backend/routers/qa.py` - 问答逻辑

### 前端调试

Streamlit 前端不支持 PyCharm 直接调试，但可以在代码中添加：
```python
import streamlit as st
st.write("调试信息:", variable_name)
```

## 七、项目配置速查

| 配置项 | 值 |
|--------|-----|
| 后端地址 | http://localhost:8000 |
| 前端地址 | http://localhost:8501 |
| API文档 | http://localhost:8000/docs |
| 数据库 | MySQL/SQLite/PostgreSQL |
| AI模型 | qwen3-max (阿里云DashScope) |

## 八、目录颜色标记（PyCharm）

设置目录类型：
1. 右键点击文件夹
2. `Mark Directory as`：
   - `backend` → `Sources Root`
   - `frontend` → `Sources Root`
   - `data` → `Excluded` (可选)
   - `result` → `Excluded` (可选)

这样可以让 PyCharm 更好地理解项目结构。

---

如有问题，查看：
- `README.md` - 项目说明
- `QUICKSTART.md` - 快速开始
- `DEPLOYMENT.md` - 部署指南
