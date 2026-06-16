# 📚 ZJU DDL 统一爬虫

爬取 **PTA（拼题 A）** + **学在浙大** 的作业截止时间，支持终端表格查看、JSON/CSV 导出、一键导入 macOS 提醒事项。

## ✨ 功能

- **双数据源**：PTA（REST API，无需浏览器）+ 学在浙大（Playwright 自动化）
- **自动分页**：一次性抓取所有作业（PTA 93 道，学在浙大全部）
- **智能去重**：过期作业自动跳过，已导入提醒事项的不重复导入
- **多种输出**：终端表格 | JSON | CSV | macOS 提醒事项
- **关键词搜索**、**状态筛选**（进行中/已结束）

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install requests rich python-dateutil playwright
playwright install chromium
```

### 2. 配置 Cookie 和账号

编辑 `zju-ddl.sh`，填入你的信息：

```bash
# PTA：浏览器登录 pintia.cn → F12 → Application → Cookies → 复制
export PTA_COOKIES="PTASession=xxx; JSESSIONID=xxx; _bl_uid=xxx"

# 学在浙大（可选）
export ZJU_USER="你的学号"
export ZJU_PASS="你的密码"
```

### 3. 运行

```bash
# 查看全部
./zju-ddl.sh

# 只看 PTA
./zju-ddl.sh --pta-only

# 只看进行中
./zju-ddl.sh --status active

# 搜索关键词
./zju-ddl.sh --keyword HW

# 导出
./zju-ddl.sh --export homework.json
./zju-ddl.sh --export homework.csv

# 导入 macOS 提醒事项（自动跳过过期和重复的）
./zju-ddl.sh --to-reminders
```

## 🔧 手动运行

```bash
source venv/bin/activate
export PTA_COOKIES="PTASession=xxx; JSESSIONID=xxx; _bl_uid=xxx"
PYTHONPATH=. python3 -m zju_ddl_scraper.cli --pta-only --to-reminders
```

## 📁 项目结构

```
zju_ddl_scraper/
├── zju-ddl.sh                    # 一键启动脚本
├── requirements.txt              # Python 依赖
├── pyproject.toml                # 项目配置
├── README.md
└── zju_ddl_scraper/
    ├── __init__.py
    ├── cli.py                    # 命令行入口
    ├── models.py                 # 数据模型
    ├── pta.py                    # PTA 爬虫（REST API）
    ├── zju.py                    # 学在浙大爬虫（Playwright）
    └── reminders.py              # macOS 提醒事项导入
```

## 🔑 PTA Cookie 获取方式

1. 用浏览器打开 https://pintia.cn 并登录
2. 按 `F12` → **Application** → **Cookies** → `pintia.cn`
3. 复制 `PTASession`、`JSESSIONID`、`_bl_uid` 的值
4. 拼成 `PTASession=xxx; JSESSIONID=xxx; _bl_uid=xxx`

## ⚠️ 注意

- PTA 爬虫走 REST API，不需要浏览器
- 学在浙大需要校内网或 VPN
- Cookie 过期后重新复制即可
