# PalmAtlas · 棕榈酰化数据库网站

一个可以直接在 VS Code 或 GitHub Codespaces 运行的 Django 网站。使用 SQLite 保存蛋白、棕榈酰化位点和证据，提供检索、详情、基础统计、CSV 导出和受登录保护的管理后台。默认不需要单独安装数据库服务器或前端构建工具。

## 在 VS Code 运行

用 VS Code 打开本仓库根目录。在“终端 → 新建终端”执行：

```bash
bash run.sh
```

脚本会创建 `.venv`、安装 `requirements.txt` 中的依赖、初始化 SQLite 表并启动网站。也可选择“终端 → 运行任务 → PalmAtlas: 启动网站”。本地打开 `http://127.0.0.1:8000/`；Codespaces 在“端口”面板打开 8000 端口。按 `Ctrl+C` 停止。`.vscode/launch.json` 提供 Python 调试配置，先运行 `bash run.sh` 安装依赖再按 F5。

## 数据录入

网站初次启动是空库。推荐复制 `data/template.csv`，填入自己的研究数据；文件按 UTF-8 CSV 保存，表头保持不变。执行：

```bash
.venv/bin/python manage.py import_records data/your_records.csv
```

或者创建管理员账号后从 `/admin/` 填入蛋白、位点与证据：

```bash
.venv/bin/python manage.py createsuperuser
```

如果只想先看界面，可执行 `.venv/bin/python manage.py import_records data/demo.csv --demo`。演示记录全部为虚构数据，网站会标注，并可在筛选条件中排除。不要把它们当成科研证据。导入同一文件会更新原记录；无效行会导致整批回滚。

## 网站功能

| 地址 | 功能 |
| --- | --- |
| `/` | 按基因、蛋白、物种、证据类型和数据范围检索；结果分页 |
| `/site/<id>/` | 蛋白信息、位点序列窗口和研究证据详情 |
| `/analysis/` | 当前筛选结果的物种、基因、证据和方法计数图 |
| `/export/` | 将当前筛选结果导出为 UTF-8 CSV |
| `/admin/` | 登录后管理蛋白、位点和证据 |

统计为描述性计数；证据图按证据条目计数，位点图按位点计数。没有显著性检验、预测模型或富集分析。

## 主要配置与个性化位置

| 文件 | 主要内容 |
| --- | --- |
| `config/settings.py` | Django、SQLite 路径、环境变量、主机配置 |
| `.env.example` | 可复制为 `.env` 的本地配置模板 |
| `palmitoylation/models.py` | 蛋白、位点、证据三张业务表与约束 |
| `palmitoylation/migrations/0001_initial.py` | 初始化数据库表的迁移 |
| `palmitoylation/views.py` | 检索、详情、统计、CSV 导出逻辑 |
| `palmitoylation/templates/palmitoylation/` | 网页模板，可修改名称与内容 |
| `palmitoylation/static/palmitoylation/style.css` | 网页颜色、排版与移动端样式 |
| `.vscode/tasks.json`、`.vscode/launch.json` | VS Code 启动、测试、迁移和调试配置 |
| `data/template.csv` | 数据填写模板 |

数据库字段和每项配置的解释见 [数据库配置说明](docs/database.md)。修改数据字段后运行 `.venv/bin/python manage.py makemigrations` 和 `.venv/bin/python manage.py migrate`。仅修改网页文案、样式或录入数据无需生成迁移。

## 检查项目

```bash
.venv/bin/python manage.py check
.venv/bin/python manage.py test palmitoylation
.venv/bin/python manage.py makemigrations --check --dry-run
```

`db.sqlite3`、`.venv` 与 `.env` 不应提交 Git。生产部署需要把 `DJANGO_DEBUG=false`、设置私有 `DJANGO_SECRET_KEY`、配置正式域名和 HTTPS，并使用生产级 Web 服务。
