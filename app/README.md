# autoWechat Console

本目录是基于 `pyweixin` 的本地 Web 控制台应用层。

## 启动后端

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

后端文档地址：

```text
http://127.0.0.1:8000/docs
```

## 启动前端开发服务

```bash
cd frontend
npm install
npm run dev
```

前端开发地址：

```text
http://127.0.0.1:5173
```

## 构建前端并由 FastAPI 托管

```bash
cd frontend
npm install
npm run build
cd ..
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

构建后访问：

```text
http://127.0.0.1:8000
```

## 可选 Token

设置环境变量后，所有 REST API 需要请求头 `x-autowechat-token`：

```powershell
$env:AUTOWECHAT_TOKEN="your-token"
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## 打包为 Windows 应用

先确保已经安装 Node.js，然后在项目根目录运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\packaging\build_windows.ps1
```

生成目录：

```text
dist\autoWechat Console\autoWechat Console.exe
```

双击 exe 后会启动本地服务，并打开内嵌 WebView 桌面窗口，不会跳转系统浏览器。
