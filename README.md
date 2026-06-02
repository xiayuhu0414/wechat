# autoWechat Console

本项目是一个 Windows 本地微信自动化控制台，使用 FastAPI 提供后端接口，Vue 3 + Element Plus 提供前端控制台，`pywebview` 提供桌面窗口入口，底层微信操作基于本仓库内保留的 `pywechat/pyweixin` 模块。

> 说明：项目用于本地自动化辅助操作微信客户端。微信版本、系统 UIA 可访问性、窗口状态都会影响稳定性，建议先在测试微信号和可控环境中验证流程。

## 主要功能

- 客户资源管理：Excel 上传预览、人工列映射、按手机号去重、保留原始表格信息、客户表分页和编辑。
- 批量添加好友：从客户表发起批量好友添加，可配置招呼语、备注等字段。
- 通讯录管理：同步好友、群聊、群成员，支持本地缓存、标签维护和好友详情同步。
- 消息与文件：批量发送消息、文件传输相关操作。
- 自动回复：配置自动回复规则，并通过任务队列启动或停止。
- 朋友圈：发布朋友圈内容，支持图片九宫格形式上传；可通过 DeepSeek 兼容接口生成朋友圈文案。
- 系统配置：微信操作参数、UIA 探测与兼容启动、AI 模型地址、Key、模型名称、温度、Token 上限等配置。
- 任务队列：异步执行耗时微信操作，前端可查看任务状态。

## 技术栈

- 后端：Python、FastAPI、Uvicorn、SQLite、openpyxl、uiautomation
- 前端：Vue 3、Vite、Element Plus
- 桌面壳：pywebview
- 打包：PyInstaller
- 测试：pytest

## 目录结构

```text
autoWechat/
|- app/                  后端应用、路由、任务、数据库和服务
|- frontend/             Vue 前端控制台
|- packaging/            Windows 打包脚本和 PyInstaller spec
|- pywechat/pyweixin/    当前实际使用的微信自动化底层模块
|- tests/                后端测试
|- launcher.py           桌面程序入口
`- requirements.txt      Python 依赖入口
```

运行过程中会生成本地数据目录，默认在：

```text
%LOCALAPPDATA%\autoWechat
```

可通过 `AUTOWECHAT_DATA_DIR` 指定其它位置。

## 环境要求

- Windows 10/11
- Python 3.12 或兼容版本
- Node.js 18+ 或 20+
- 已安装并登录 Windows 微信客户端

## 本地开发启动

安装 Python 依赖：

```powershell
python -m pip install -r requirements.txt
```

启动后端：

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

后端接口文档：

```text
http://127.0.0.1:8000/docs
```

启动前端开发服务：

```powershell
cd frontend
npm install
npm run dev
```

前端开发地址：

```text
http://127.0.0.1:5173
```

## 构建前端并由后端托管

```powershell
cd frontend
npm install
npm run build
cd ..
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

访问：

```text
http://127.0.0.1:8000
```

## 启动桌面控制台

开发环境下可以直接运行：

```powershell
python launcher.py
```

程序会启动本地 FastAPI 服务，并打开 `autoWechat Console` 桌面窗口。

## Windows 打包

在项目根目录运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\packaging\build_windows.ps1
```

打包产物：

```text
dist\autoWechat Console\autoWechat Console.exe
```

## 常用环境变量

| 变量 | 说明 | 默认值 |
| --- | --- | --- |
| `AUTOWECHAT_HOST` | 后端监听地址 | `127.0.0.1` |
| `AUTOWECHAT_PORT` | 后端监听端口 | `8000` |
| `AUTOWECHAT_TOKEN` | API 访问令牌，设置后请求需携带 `x-autowechat-token` | 空 |
| `AUTOWECHAT_DATA_DIR` | 本地数据库、上传文件、日志、诊断文件目录 | `%LOCALAPPDATA%\autoWechat` |

示例：

```powershell
$env:AUTOWECHAT_TOKEN="your-token"
$env:AUTOWECHAT_DATA_DIR="D:\autoWechatData"
python launcher.py
```

## AI 文案配置

朋友圈文案生成功能使用 OpenAI Chat Completions 兼容接口。可在前端“系统配置”中配置：

- API Base URL，例如 `https://api.deepseek.com`
- API Key
- 模型名称
- Temperature
- Max Tokens
- Timeout
- System Prompt

配置会保存在本地 SQLite 数据库中，接口返回配置时不会明文返回 Key。

## 测试

```powershell
python -m pytest -q
python -m compileall -q launcher.py app pywechat\pyweixin
```

前端构建验证：

```powershell
cd frontend
npm install
npm run build
```

## 注意事项

- 微信自动化依赖真实 Windows 桌面环境，远程桌面最小化、微信窗口被遮挡、微信版本变化都可能导致 UIA 操作失败。
- 运行批量好友、批量消息等功能前，建议先小批量测试。
- `data/`、`dist/`、`frontend/node_modules/`、缓存目录和打包产物不会提交到仓库。
- 如果微信 UI 树不可见，可在系统配置中使用 UIA 探测和兼容启动相关功能辅助排查。
