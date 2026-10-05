# -*- coding: utf-8 -*-
"""
自动化 EDA（探索性数据分析）脚本
====================================
功能：
  1. 自动读取 CSV / Excel（.xlsx/.xls）数据文件
  2. 使用 ydata-profiling 生成标准 HTML 报告
     （含 Overview / Variables / Interactions / Correlations / Missing / Sample）
  3. 自动处理 Windows 中文编码与中文字体
  4. 若未安装 ydata-profiling，提供内置轻量 EDA 兜底输出

用法：
  python auto_eda.py <数据文件路径> [-o 输出报告文件名] [-t 标题]

示例：
  python auto_eda.py data.csv
  python auto_eda.py sales.xlsx -o sales_report.html -t 销售数据EDA
"""

import os
import sys
import argparse
import warnings

# 避免在受限/受控目录写入 .pyc 缓存
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
sys.dont_write_bytecode = True

# Windows 控制台 UTF-8 输出，避免中文/特殊字符触发 UnicodeEncodeError
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

warnings.filterwarnings("ignore")


def setup_chinese_font():
    """配置 matplotlib 中文字体，避免图表乱码。"""
    try:
        import matplotlib
        matplotlib.use("Agg")  # 无界面环境也能出图
        from matplotlib import rcParams

        # 按优先级选择可用的中文字体
        candidates = [
            "Microsoft YaHei",
            "SimHei",
            "SimSun",
            "KaiTi",
            "FangSong",
            "Arial Unicode MS",
            "Noto Sans CJK SC",
            "WenQuanYi Micro Hei",
        ]
        rcParams["font.sans-serif"] = candidates + rcParams.get("font.sans-serif", [])
        rcParams["axes.unicode_minus"] = False  # 解决负号显示
        return True
    except Exception:
        return False


def read_data(file_path):
    """根据扩展名自动读取 CSV 或 Excel。"""
    import pandas as pd

    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".csv":
        # 尝试常见中文编码
        for enc in ("utf-8-sig", "utf-8", "gbk", "gb18030"):
            try:
                return pd.read_csv(file_path, encoding=enc)
            except (UnicodeDecodeError, UnicodeError):
                continue
        # 兜底：用 python 引擎 + 错误忽略
        return pd.read_csv(file_path, encoding="utf-8", engine="python",
                           encoding_errors="ignore")

    elif ext in (".xlsx", ".xls"):
        try:
            return pd.read_excel(file_path)
        except ImportError:
            print("[提示] 缺少 openpyxl，正在尝试安装后重试...")
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", "openpyxl"])
            return pd.read_excel(file_path)

    elif ext in (".tsv", ".txt"):
        return pd.read_csv(file_path, sep="\t", encoding="utf-8-sig")

    else:
        raise ValueError(f"不支持的文件格式：{ext}（支持 .csv .xlsx .xls .tsv .txt）")


def translate_report_to_chinese(html_path):
    """将 ydata-profiling 生成的英文报告批量翻译为中文（固定 UI 文案替换）。"""
    # 长词优先，避免短词误伤（例如 "Mean" 先于 "Mea"）
    mapping = [
        # 导航 / 模块标题
        ("Overview", "概览"),
        ("Variables", "变量"),
        ("Interactions", "交互分析"),
        ("Correlations", "相关性"),
        ("Missing values", "缺失值"),
        ("Missing value", "缺失值"),
        ("Sample", "样本"),
        ("Duplicates", "重复行"),
        ("Duplicate rows", "重复行"),
        ("Alerts", "警告"),
        ("Reproduction", "复现"),

        # 概览统计
        ("Number of variables", "变量数"),
        ("Number of observations", "观测值数"),
        ("Missing cells", "缺失单元格"),
        ("Missing cells (%)", "缺失率(%)"),
        ("Duplicate rows", "重复行"),
        ("Duplicate rows (%)", "重复率(%)"),
        ("Total size in memory", "内存占用"),
        ("Average record size in memory", "平均记录大小"),
        ("Number of numeric columns", "数值列数"),
        ("Number of categorical columns", "分类列数"),
        ("Number of date/time columns", "日期/时间列数"),
        ("Number of boolean columns", "布尔列数"),

        # 变量详情
        ("Distinct", "唯一值数"),
        ("Distinct count", "唯一值计数"),
        ("Unique", "唯一"),
        ("Unique count", "唯一值计数"),
        ("Most frequent", "众数"),
        ("Mean", "均值"),
        ("Median", "中位数"),
        ("Minimum", "最小值"),
        ("Maximum", "最大值"),
        ("Min value", "最小值"),
        ("Max value", "最大值"),
        ("Range", "极差"),
        ("Interquartile range", "四分位距"),
        ("Standard deviation", "标准差"),
        ("Coefficient of variation", "变异系数"),
        ("Mean absolute deviation", "平均绝对偏差"),
        ("Quantile statistics", "分位数统计"),
        ("Descriptive statistics", "描述性统计"),
        ("Value counts", "值计数"),
        ("Extreme values", "极值"),
        ("5 most frequent values", "出现频率最高的5个值"),
        ("First n items", "前n项"),

        # 分位数
        ("minimum", "最小值"),
        ("Q1", "下四分位数"),
        ("Q3", "上四分位数"),
        ("maximum", "最大值"),
        ("Skewness", "偏度"),
        ("Kurtosis", "峰度"),

        # 缺失值
        ("Count", "数量"),
        ("Frequency", "频率"),
        ("Missing", "缺失"),
        ("Missing (%)", "缺失率(%)"),
        ("n_missing", "缺失数"),
        ("p_missing", "缺失率"),

        # 相关性
        ("Pearson", "皮尔逊"),
        ("Spearman", "斯皮尔曼"),
        ("Kendall", "肯德尔"),
        ("Phi_k", "Phi_k"),
        ("Cramér's V", "克莱默V"),
        ("Correlation matrix", "相关系数矩阵"),

        # 类型
        ("Numeric", "数值型"),
        ("Categorical", "分类型"),
        ("Boolean", "布尔型"),
        ("Date", "日期"),
        ("DateTime", "日期时间"),
        ("Time", "时间"),
        ("Text", "文本"),
        ("Unsupported", "不支持"),

        # 交互
        ("Toggle all", "全部切换"),
        ("Scatter plot", "散点图"),
        ("Select a column", "选择一列"),

        # 警告类型
        ("constant", "常量列"),
        ("constant_length", "常量长度"),
        ("high_cardinality", "高基数"),
        ("uniform_distribution", "均匀分布"),
        ("zero_inflated", "零膨胀"),
        ("image", "图像"),
        ("unsupported", "不支持"),

        # 其他
        ("Value", "值"),
        ("Frequency (%)", "频率(%)"),
        ("Length", "长度"),
        ("generated", "生成于"),
        ("Report generated", "报告生成"),
        ("Powered by", "由...提供支持"),
    ]

    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    # 仅替换可见文本：用一个临时标记避免误替换 HTML 标签/属性中的词
    # 这里采用简单策略：对每个英文词做全词替换（ydata-profiling 文案多为独立短语）
    for en, zh in mapping:
        # 替换 >英文< 形式（标签内文本）
        html = html.replace(f">{en}<", f">{zh}<")
        # 替换标题属性
        html = html.replace(f'title="{en}"', f'title="{zh}"')
        html = html.replace(f'aria-label="{en}"', f'aria-label="{zh}"')
        # 替换 tab/导航中的纯文本（带空格边界）
        html = html.replace(f">{en} ", f">{zh} ")

    # 替换报告的语言声明
    html = html.replace('<html lang="en">', '<html lang="zh-CN">')
    html = html.replace('lang="en"', 'lang="zh-CN"')

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)


def run_profiling_report(df, output_path, title):
    """使用 ydata-profiling 生成标准 EDA HTML 报告。"""
    try:
        from ydata_profiling import ProfileReport
    except ImportError:
        try:
            from pandas_profiling import ProfileReport  # 旧版本名兼容
        except ImportError:
            return False

    profile = ProfileReport(
        df,
        title=title,
        explorative=True,
        minimal=False,
        # 相关性计算时只对数值列，避免混合类型报错（ydata-profiling 内部已处理，此处显式配置）
        correlations={
            "pearson": {"calculate": True},
            "spearman": {"calculate": True},
            "kendall": {"calculate": False},
            "phi_k": {"calculate": False},
            "cramers": {"calculate": False},
        },
        # 缺失值模块
        missing_diagrams={"bar": True, "matrix": True, "heatmap": True},
    )
    profile.to_file(output_path)

    # 生成后翻译为中文
    try:
        translate_report_to_chinese(output_path)
    except Exception as e:
        print(f"[警告] 报告中文化处理失败：{e}（报告仍为英文）")

    return True


def run_builtin_eda(df, output_path, title):
    """内置轻量 EDA：当 ydata-profiling 不可用时的兜底方案。"""
    import pandas as pd
    import numpy as np

    setup_chinese_font()
    import matplotlib.pyplot as plt
    try:
        import seaborn as sns
        HAS_SNS = True
    except ImportError:
        HAS_SNS = False

    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = df.select_dtypes(exclude=[np.number]).columns.tolist()

    # 1. 概览
    overview = pd.DataFrame({
        "指标": ["行数", "列数", "数值列数", "分类列数",
                 "缺失值总数", "重复行数", "总内存(KB)"],
        "值": [
            len(df), df.shape[1], len(num_cols), len(cat_cols),
            int(df.isna().sum().sum()),
            int(df.duplicated().sum()),
            round(df.memory_usage(deep=True).sum() / 1024, 2),
        ],
    })

    # 2. 缺失值统计
    missing = pd.DataFrame({
        "列名": df.columns,
        "缺失数": df.isna().sum().values,
        "缺失率(%)": (df.isna().mean().values * 100).round(2),
    })

    # 3. 数值列描述
    num_desc = df[num_cols].describe().T if num_cols else pd.DataFrame()

    # 4. 分类列描述
    cat_desc = df[cat_cols].describe().T if cat_cols else pd.DataFrame()

    # 5. 相关性（仅数值列）
    if num_cols:
        corr = df[num_cols].corr()
    else:
        corr = pd.DataFrame()

    # 生成图表
    os.makedirs("_eda_assets", exist_ok=True)

    figs = []
    # 缺失值柱状图
    if not df.isna().sum().sum() == 0:
        plt.figure(figsize=(10, 5))
        df.isna().sum().sort_values(ascending=False).head(20).plot(kind="bar")
        plt.title("缺失值数量 Top20")
        plt.tight_layout()
        p = os.path.join("_eda_assets", "missing.png")
        plt.savefig(p, dpi=100, bbox_inches="tight")
        plt.close()
        figs.append(("缺失值分布", p))

    # 相关性热力图
    if len(num_cols) >= 2:
        plt.figure(figsize=(10, 8))
        if HAS_SNS:
            sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", center=0)
        else:
            im = plt.imshow(corr.values, cmap="coolwarm", vmin=-1, vmax=1)
            plt.colorbar(im)
            plt.xticks(range(len(corr.columns)), corr.columns, rotation=45, ha="right")
            plt.yticks(range(len(corr.columns)), corr.columns)
            for i in range(len(corr.columns)):
                for j in range(len(corr.columns)):
                    plt.text(j, i, f"{corr.values[i, j]:.2f}",
                             ha="center", va="center", fontsize=9)
        plt.title("数值列相关性热力图")
        plt.tight_layout()
        p = os.path.join("_eda_assets", "corr.png")
        plt.savefig(p, dpi=100, bbox_inches="tight")
        plt.close()
        figs.append(("相关性热力图", p))

    # 数值列分布直方图
    for c in num_cols[:8]:
        plt.figure(figsize=(7, 4))
        df[c].dropna().hist(bins=30)
        plt.title(f"{c} 分布")
        plt.tight_layout()
        p = os.path.join("_eda_assets", f"hist_{c}.png")
        plt.savefig(p, dpi=100, bbox_inches="tight")
        plt.close()
        figs.append((f"{c} 分布", p))

    # 拼装 HTML
    def df_to_html(d, caption):
        if d is None or d.empty:
            return f"<h3>{caption}</h3><p>无数据</p>"
        return (f"<h3>{caption}</h3>" +
                d.to_html(classes="tbl", border=0, justify="left"))

    fig_html = "".join(
        f'<div class="fig"><h3>{name}</h3><img src="{path}" /></div>'
        for name, path in figs
    )

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<title>{title}</title>
<style>
body{{font-family:"Microsoft YaHei",Arial,sans-serif;margin:30px;line-height:1.6}}
h1{{color:#2c3e50}} h2{{color:#34495e;border-bottom:2px solid #3498db;padding-bottom:5px}}
.tbl{{border-collapse:collapse;margin:10px 0;font-size:13px}}
.tbl th,.tbl td{{border:1px solid #ddd;padding:6px 10px;text-align:left}}
.tbl th{{background:#3498db;color:#fff}}
.fig{{margin:20px 0}} .fig img{{max-width:100%;border:1px solid #eee}}
</style>
</head>
<body>
<h1>{title}</h1>
{df_to_html(overview, "1. 数据概览")}
{df_to_html(missing, "2. 缺失值统计")}
{df_to_html(num_desc, "3. 数值列描述统计")}
{df_to_html(cat_desc, "4. 分类列描述统计")}
<h2>5. 可视化图表</h2>
{fig_html}
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    return True


def main():
    parser = argparse.ArgumentParser(description="自动化 EDA 报告生成工具")
    parser.add_argument("input", help="数据文件路径（.csv / .xlsx / .xls）")
    parser.add_argument("-o", "--output", default=None, help="输出 HTML 文件名")
    parser.add_argument("-t", "--title", default="自动化 EDA 报告", help="报告标题")
    args = parser.parse_args()

    if not os.path.isfile(args.input):
        print(f"[错误] 文件不存在：{args.input}")
        sys.exit(1)

    print(f"[1/4] 读取数据：{args.input}")
    try:
        df = read_data(args.input)
    except Exception as e:
        print(f"[错误] 读取数据失败：{e}")
        sys.exit(1)

    print(f"      数据形状：{df.shape[0]} 行 x {df.shape[1]} 列")

    setup_chinese_font()

    output = args.output or f"eda_report_{os.path.splitext(os.path.basename(args.input))[0]}.html"

    print("[2/4] 尝试使用 ydata-profiling 生成标准报告...")
    used = "ydata-profiling"
    ok = run_profiling_report(df, output, args.title)

    if not ok:
        print("[提示] 未检测到 ydata-profiling，使用内置轻量 EDA 兜底。")
        print("      安装标准工具可获得更完整报告：pip install ydata-profiling")
        used = "内置轻量EDA"
        ok = run_builtin_eda(df, output, args.title)

    if not ok:
        print("[错误] 报告生成失败。")
        sys.exit(1)

    print(f"[3/4] 报告已生成：{output}")
    print(f"[4/4] 完成。使用引擎：{used}")
    print(f"      请用浏览器打开 {os.path.abspath(output)} 查看报告。")


if __name__ == "__main__":
    main()
