# AdmitCardServer 准考证服务系统

## 项目简介

这是一个基于Go语言的Web服务，用于管理和提供准考证PDF文件的下载服务。

## 系统要求

- Go 1.16+ 版本
- Git（可选，用于克隆仓库）

## 安装与部署

### 1. 克隆仓库（可选）

```bash
git clone https://github.com/your-repo/AdmitCardServer.git
cd AdmitCardServer
```

### 2. 安装依赖

```bash
go mod download
```

### 3. 运行服务

```bash
go run main.go
```

服务默认运行在 `http://localhost:8080`

## 使用方法

1. 将准考证PDF文件放入 `AdmitCards/` 目录，命名格式为：`身份证号-姓名.pdf`
2. 访问 `http://localhost:8080` 进入系统
3. 输入身份证号查询并下载准考证

## 文件结构说明

```
AdmitCardServer/
├── go.mod            # Go模块定义
├── go.sum            # 依赖校验
├── main.go           # 主程序入口
├── handler.go        # 请求处理器
├── rate_limiter.go   # 限流中间件
├── AdmitCards/       # 准考证PDF存储目录
├── assets/           # 静态资源
│   ├── css/          # CSS样式
│   └── js/           # JavaScript脚本
└── templates/        # HTML模板
    └── index.html    # 首页模板
```

## 许可证

MIT License
