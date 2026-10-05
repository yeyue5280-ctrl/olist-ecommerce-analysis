# Data Analysis Toolkit 数据分析工具箱

一套用 Python 编写的数据分析效率工具，包含**数据清洗工具库**和**自动化 EDA 报告生成**两大模块，旨在减少重复性工作、提升分析效率。

## 功能特性

### 1. 数据清洗工具库（data_cleaner.py）

封装 6 类常用清洗操作，支持链式调用，自动生成清洗报告。

| 功能 | 说明 |
|------|------|
| 缺失值处理 | 均值/中位数/众数填充、删除高缺失列、标记法、前向/后向填充 |
| 异常值处理 | IQR 方法 / 3σ 原则，支持标记、删除、截断三种处理方式 |
| 类型转换 | 自动识别金额列（$€£¥）、日期列、数字字符串并自动转换 |
| 重复值处理 | 自动检测并去重，支持指定列 |
| 文本清洗 | 去空格、统一大小写、去除特殊字符、压缩连续空格 |
| 一键清洗 | `clean_all()` 一行代码完成全部常规清洗步骤 |

**使用示例：**

```python
from data_cleaner import DataCleaner

cleaner = DataCleaner(df)
df_clean = cleaner.clean_all().get_data()
print(cleaner.get_report())
```

### 2. 自动化 EDA（auto_eda.py）

一键生成专业级探索性数据分析报告，输出为 HTML 格式。

- 支持 CSV / Excel 格式输入，自动识别中文编码
- 基于 ydata-profiling 生成标准报告（概览/变量/相关性/缺失值/样本）
- **报告中文化**：自动将 UI 文案翻译为中文
- 轻量版兜底：未安装 ydata-profiling 时使用内置方案
- 中文字体自动配置，图表无乱码

**使用方法：**

```bash
python auto_eda.py data.csv
python auto_eda.py sales.xlsx -o sales_report.html -t 销售数据EDA
```

## 技术栈

- Python 3.8+
- pandas / numpy
- ydata-profiling（可选，用于标准报告）
- matplotlib / seaborn
- argparse（命令行接口）

## 项目亮点

- **工程化设计**：面向对象封装、链式调用、异常处理完善
- **中文友好**：编码自动检测、中文字体配置、报告中文化
- **容错机制**：缺失依赖自动降级、多种编码尝试、错误兜底
- **开箱即用**：零配置一键运行，适合快速上手

## 目录结构

```
data-analysis-toolkit/
├── data_cleaner.py    # 数据清洗工具库
├── auto_eda.py        # 自动化 EDA 报告生成
└── README.md
```

## 开发说明

本项目使用 GitHub Copilot 辅助开发，采用"需求拆解 → 分步生成 → 单元验证 → 人工重构"四步法，在保证代码质量的同时提升开发效率。
