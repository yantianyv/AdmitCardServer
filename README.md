# AdmitCardServer 准考证服务系统

## 项目简介

这是一个基于Go语言的Web服务，配合Python脚本实现准考证生成和管理功能。系统包含：

- 使用generator.py从Excel生成准考证PDF
- 提供Web界面查询和下载准考证
- 内置频率限制保护

## 系统要求

- Go 1.16+ 版本
- Python 3.6+
- Git（可选，用于克隆仓库）

## 安装与部署

### 1. 克隆仓库（可选）

```bash
git clone https://github.com/yantianyv/AdmitCardServer.git
cd AdmitCardServer
```

### 2. 安装依赖

#### Go依赖

```bash
go mod download
```

#### Python依赖

```bash
pip install -r requirements.txt
```

### 3. 运行服务

```bash
go run main.go
```

服务默认运行在 `http://localhost:8080`

## 生成准考证

### 1. 准备Excel文件

- 第一列：姓名
- 第二列：身份证号
- 其他列：自定义字段（可选）

### 2. 运行生成器

```bash
python generator.py 考生信息.xlsx [-c 配置名]
```

- 默认使用config/default.json配置
- 生成的PDF保存在AdmitCards目录

### 3. 自定义配置

编辑config/default.json或创建新配置文件：

```json
{
  "exam_name": "考试名称",
  "exam_location": "考试地点",
  "exam_schedule": [
    {"subject": "科目1", "time": "时间1"},
    {"subject": "科目2", "time": "时间2"}
  ],
  "exam_notes": [
    "注意事项1",
    "注意事项2"
  ]
}
```

## 使用准考证服务

1. 访问 `http://localhost:8080` 进入系统
2. 输入姓名和身份证号查询
3. 系统会自动下载匹配的准考证

## 文件结构说明

```
AdmitCardServer/
├── go.mod            # Go模块定义
├── go.sum            # Go依赖校验
├── main.go           # 主程序入口
├── generator.py      # 准考证生成脚本
├── requirements.txt  # Python依赖
├── config/           # 配置文件目录
│   └── default.json  # 默认配置
├── AdmitCards/       # 准考证PDF存储目录
├── assets/           # 静态资源
│   ├── css/          # CSS样式
│   └── js/           # JavaScript脚本
├── fonts/            # 字体文件
├── templates/        # HTML模板
│   └── index.html    # 首页模板
└── output/           # 临时输出目录
```

## 许可证

MIT License
