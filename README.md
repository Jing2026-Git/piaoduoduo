# 🎫 票多多 (PiaoDuoDuo)

> 演唱会票价智能比价与资讯追踪工具 —— 帮你找到最划算的演唱会门票

[![Python 3.8+](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Flask 2.2](https://img.shields.io/badge/Flask-2.2+-green.svg)](https://flask.palletsprojects.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## ✨ 项目特点

- 🎯 **多平台采集**：同时从大麦网、猫眼演出等主流售票平台采集演唱会信息
- 💰 **智能比价**：同一场演出跨平台对比票价，综合性价比评分推荐
- 📊 **数据可视化**：票价柱状图、平台饼图、城市分布图，一目了然
- 📈 **价格历史**：记录历次搜索的票价数据，追踪价格变化趋势
- 🎟️ **开票提醒**：检测各场次的在售/已售罄状态
- 🌐 **Web 界面**：美观的可视化界面，支持一键搜索与图表展示
- 💻 **命令行工具**：支持脚本化操作，导出 CSV/JSON 数据
- 🔌 **API 接口**：提供 JSON API，便于集成到其他系统

---

## 📁 项目结构

```
piaoduoduo/
├── src/
│   ├── collectors/          # 数据采集模块
│   │   ├── damai.py         # 大麦网采集器
│   │   └── maoyan.py        # 猫眼演出采集器
│   ├── models.py            # 核心数据模型
│   ├── cleaner.py           # 数据清洗 & 去重
│   ├── comparator.py        # 票价对比 & 智能推荐
│   ├── visualizer.py        # 图表可视化数据生成
│   ├── database.py          # SQLite 数据库管理
│   └── piaoduoduo.py        # 主应用类（协调器）
├── web/
│   ├── templates/           # HTML 模板
│   │   ├── base.html        # 基础布局
│   │   ├── index.html       # 首页
│   │   ├── search_result.html  # 搜索结果
│   │   ├── charts.html      # 数据图表
│   │   ├── demo.html        # 功能演示
│   │   └── 404.html         # 404 页面
│   ├── static/
│   │   ├── css/style.css    # 全局样式
│   │   └── js/app.js        # 前端交互脚本
│   └── app.py               # Flask 应用主程序
├── cli.py                   # 命令行工具入口
├── requirements.txt         # Python 依赖包
└── README.md                # 项目说明文档
```

---

## 🚀 快速开始

### 方式一：Web 界面（推荐）

```bash
# 1. 安装依赖
pip install flask requests beautifulsoup4 lxml

# 2. 启动 Web 服务
cd piaoduoduo
python -m flask --app web.app run --host 0.0.0.0 --port 5000

# 3. 浏览器访问
# 打开 http://localhost:5000
```

### 方式二：命令行使用

```bash
# 演示模式（使用示例数据，无需网络）
python cli.py demo --keyword "周杰伦"

# 搜索演出信息
python cli.py search "周杰伦"
python cli.py search "演唱会" --city "北京"

# 票价对比分析
python cli.py compare "周杰伦"

# 导出数据
python cli.py export --keyword "周杰伦" --format csv
python cli.py export --keyword "演唱会" --format json

# 查看数据统计
python cli.py stats

# 启动 Web 界面
python cli.py web
```

### 方式三：API 调用

```bash
# 搜索演出（返回 JSON）
curl "http://localhost:5000/api/search?keyword=周杰伦&mode=sample"

# 查看统计信息
curl "http://localhost:5000/api/stats"

# 检查开票状态
curl "http://localhost:5000/api/availability?keyword=周杰伦"

# 导出 CSV
curl "http://localhost:5000/export/csv?keyword=周杰伦&mode=sample" -o result.csv
```

---

## 🌐 路由列表

| 路径 | 方法 | 功能 |
|-----|-----|------|
| `/` | GET | 首页 |
| `/search` | GET/POST | 搜索结果页面 |
| `/charts` | GET | 数据可视化图表 |
| `/demo` | GET | 功能演示页 |
| `/api/search` | GET | API - 搜索（JSON） |
| `/api/stats` | GET | API - 统计信息 |
| `/api/availability` | GET | API - 开票状态 |
| `/export/csv` | GET | 导出 CSV |
| `/export/json` | GET | 导出 JSON |

---

## 🔧 技术栈

### 后端
- **Python 3.8+** —— 核心开发语言
- **Flask 2.2+** —— Web 应用框架
- **SQLite** —— 轻量级数据库（无需额外配置）
- **Requests** —— HTTP 请求库
- **BeautifulSoup4 + lxml** —— HTML 解析

### 前端
- **HTML5 + Bootstrap 5.1** —— UI 框架
- **ECharts 5.4** —— 图表可视化
- **Bootstrap Icons** —— 图标库
- **Jinja2** —— 模板引擎（Flask 内置）

---

## 🧠 核心算法

### 1. 数据采集模式
```
自动模式 (auto):
  ├─ 尝试调用目标平台真实接口
  ├─ 成功 → 返回真实数据
  └─ 失败 → 自动降级到示例数据模式

示例数据模式 (sample):
  └─ 生成结构完整的模拟数据，保证功能可演示

真实数据模式 (real):
  └─ 仅调用真实接口，失败即报错
```

### 2. 智能去重
基于「标题核心关键词 + 城市 + 日期」的多维度匹配算法，自动识别不同平台上的同一场演出。

### 3. 性价比评分
综合考虑以下因素进行加权评分：
- **价格因素 (40%)**：价格越低评分越高
- **座次因素 (30%)**：VIP/内场 > 看台前排 > 普通看台
- **可用因素 (20%)**：在售票档更有价值
- **平台因素 (10%)**：平台口碑与服务评分

---

## 📊 功能演示样例

以「周杰伦演唱会」搜索为例：

```
✅ 采集完成：大麦网 14 场，猫眼演出 7 场
✅ 数据清洗：21 场有效演出
✅ 去重合并：15 场独立演出对比

📊 数据统计：
  ├─ 覆盖城市：7 个（北京/上海/广州/深圳/成都/杭州/南京）
  ├─ 票价范围：¥199 - ¥1980
  ├─ 平均票价：¥833
  └─ 售票平台：大麦网 / 猫眼演出

💡 性价比推荐：
  1. 音乐节专场（北京） - 最低 ¥199（大麦网）
  2. LIVE 2026（上海） - 最低 ¥252（猫眼演出）
  3. 嘉年华世界巡演（广州） - 最低 ¥342（猫眼演出）
```

---

## ⚠️ 免责声明

- 本工具**仅供学习和个人使用**
- 数据来源于公开售票平台，版权归原平台所有
- 请勿将本工具用于商业用途或大规模爬虫
- 购票请通过官方渠道，谨防受骗

---

## 📝 License

MIT License —— 欢迎自由使用、修改和分发

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

⭐ 如果这个项目对您有帮助，欢迎点个 Star 支持一下！
