# -*- coding: utf-8 -*-
"""
数据清洗自动化工具库
====================
提供以下功能：
  1. 缺失值处理：均值 / 中位数 / 众数填充、删除、标记
  2. 异常值处理：3σ 原则、IQR 方法，支持标记/删除/截断
  3. 数据类型转换：自动识别日期列、金额列（处理 $ 符号）
  4. 重复值处理：自动检测并去重
  5. 文本清洗：去空格、统一大小写、特殊字符处理
  6. 一键清洗：调用一个函数完成所有常规清洗步骤

用法示例：
    from data_cleaner import DataCleaner
    import pandas as pd

    df = pd.read_csv("data.csv")
    cleaner = DataCleaner(df)
    df_clean = cleaner.clean_all().get_data()   # 一键清洗
    print(cleaner.get_report())                  # 查看清洗报告
"""

import re
import warnings
import pandas as pd
import numpy as np

warnings.filterwarnings("ignore")


class DataCleaner:
    """数据清洗器，支持链式调用。"""

    def __init__(self, df):
        self.df = df.copy()
        self.report = {
            "原始行数": len(df),
            "原始列数": df.shape[1],
            "步骤": [],
        }

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------
    def get_data(self):
        """返回清洗后的 DataFrame。"""
        return self.df

    def get_report(self):
        """返回清洗报告（字典）。"""
        return self.report

    def _log(self, step, detail):
        self.report["步骤"].append({"步骤": step, "详情": detail})

    @staticmethod
    def _is_money_series(s):
        """判断一个 Series 是否是金额列（含 $、€、£、¥ 或千分位逗号）。"""
        if s.dtype != "object":
            return False
        sample = s.dropna().astype(str).head(50)
        if sample.empty:
            return False
        money_pattern = re.compile(r"[\$€£¥]|^\d{1,3}(,\d{3})+(\.\d+)?$")
        return sample.str.contains(money_pattern, na=False).mean() > 0.5

    @staticmethod
    def _parse_money(val):
        """把金额字符串解析为浮点数（去掉 $、€、£、¥、逗号、空格）。"""
        if pd.isna(val):
            return np.nan
        s = str(val).strip()
        s = re.sub(r"[\$€£¥,\s]", "", s)
        # 处理括号表示负数：(1,234.56) -> -1234.56
        if s.startswith("(") and s.endswith(")"):
            s = "-" + s[1:-1]
        try:
            return float(s)
        except ValueError:
            return np.nan

    @staticmethod
    def _is_datetime_series(s):
        """判断一个 object 列是否可以转为日期。"""
        if s.dtype != "object":
            return False
        sample = s.dropna().astype(str).head(30)
        if sample.empty:
            return False
        try:
            converted = pd.to_datetime(sample, errors="coerce", infer_datetime_format=True)
            return converted.notna().mean() > 0.8
        except Exception:
            return False

    # ------------------------------------------------------------------
    # 1. 缺失值处理
    # ------------------------------------------------------------------
    def handle_missing(self, strategy="auto", threshold=0.5, fill_value=None):
        """
        处理缺失值。

        Parameters
        ----------
        strategy : str
            - 'auto'    : 数值列用中位数、分类/文本列用众数、日期列用众数
            - 'mean'    : 数值列均值填充
            - 'median'  : 数值列中位数填充
            - 'mode'    : 众数填充
            - 'drop'    : 删除缺失值超过 threshold 的列，其余行删除
            - 'mark'    : 新增一列标记是否缺失（原缺失用占位值填充）
            - 'ffill'/'bfill' : 前向/后向填充
        threshold : float
            缺失率超过该比例的列直接删除（0~1），仅在 auto/drop 时生效
        fill_value : any
            自定义填充值（strategy 为 mode 时可不填）
        """
        df = self.df
        total_missing = int(df.isna().sum().sum())

        # 先删除缺失率过高的列
        high_missing_cols = df.columns[df.isna().mean() > threshold].tolist()
        if high_missing_cols:
            df = df.drop(columns=high_missing_cols)
            self._log("删除高缺失列", f"缺失率>{threshold} 的列已删除：{high_missing_cols}")

        missing_before = int(df.isna().sum().sum())

        if strategy == "drop":
            before = len(df)
            df = df.dropna()
            self._log("删除缺失行", f"删除 {before - len(df)} 行含缺失值的记录")

        elif strategy == "mark":
            for col in df.columns[df.isna().any()]:
                df[f"{col}_is_missing"] = df[col].isna().astype(int)
                if df[col].dtype == "object":
                    df[col] = df[col].fillna("__MISSING__")
                else:
                    df[col] = df[col].fillna(df[col].median() if df[col].dtype != "object" else "__MISSING__")
            self._log("标记缺失值", f"为 {df.isna().sum().sum() > 0} 个有缺失的列新增标记列")

        elif strategy in ("ffill", "bfill"):
            df = df.ffill() if strategy == "ffill" else df.bfill()
            # 边界还剩的缺失用后/前向补
            df = df.bfill() if strategy == "ffill" else df.ffill()
            self._log(f"{strategy}填充", "前向/后向填充缺失值")

        else:  # auto / mean / median / mode / 自定义
            num_cols = df.select_dtypes(include=[np.number]).columns
            cat_cols = df.select_dtypes(exclude=[np.number]).columns

            for col in num_cols:
                if df[col].isna().any():
                    if strategy == "mean":
                        val = df[col].mean()
                    elif strategy == "mode":
                        val = df[col].mode().iloc[0] if not df[col].mode().empty else df[col].median()
                    else:  # auto / median
                        val = df[col].median()
                    df[col] = df[col].fillna(val)

            for col in cat_cols:
                if df[col].isna().any():
                    if fill_value is not None:
                        val = fill_value
                    else:
                        val = df[col].mode().iloc[0] if not df[col].mode().empty else "未知"
                    df[col] = df[col].fillna(val)

            self._log("填充缺失值", f"策略={strategy}，共填充 {missing_before - int(df.isna().sum().sum())} 个缺失")

        self.df = df
        self.report["缺失值处理"] = f"原缺失 {total_missing} 个，处理后剩余 {int(self.df.isna().sum().sum())} 个"
        return self

    # ------------------------------------------------------------------
    # 2. 异常值处理
    # ------------------------------------------------------------------
    def handle_outliers(self, method="iqr", action="mark", factor=1.5, sigma=3):
        """
        处理异常值（仅对数值列）。

        Parameters
        ----------
        method : str
            - 'iqr'  : IQR 方法，边界 = Q1 - factor*IQR ~ Q3 + factor*IQR
            - '3sigma': 3σ 原则，边界 = mean ± sigma*std
        action : str
            - 'mark'  : 新增 is_outlier 列标记（不删除数据）
            - 'remove': 删除异常值所在行
            - 'clip'  : 截断到边界值
        factor : float
            IQR 倍数（默认 1.5）
        sigma : float
            σ 倍数（默认 3）
        """
        df = self.df
        num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        outlier_count = 0

        if method == "3sigma":
            for col in num_cols:
                mean = df[col].mean()
                std = df[col].std()
                lower = mean - sigma * std
                upper = mean + sigma * std
                mask = (df[col] < lower) | (df[col] > upper)
                outlier_count += int(mask.sum())
                if action == "remove":
                    df = df[~mask]
                elif action == "clip":
                    df[col] = df[col].clip(lower, upper)
                else:
                    df[f"{col}_outlier"] = mask.astype(int)
        else:  # iqr
            for col in num_cols:
                q1 = df[col].quantile(0.25)
                q3 = df[col].quantile(0.75)
                iqr = q3 - q1
                lower = q1 - factor * iqr
                upper = q3 + factor * iqr
                mask = (df[col] < lower) | (df[col] > upper)
                outlier_count += int(mask.sum())
                if action == "remove":
                    df = df[~mask]
                elif action == "clip":
                    df[col] = df[col].clip(lower, upper)
                else:
                    df[f"{col}_outlier"] = mask.astype(int)

        self.df = df
        self._log("异常值处理",
                  f"方法={method}，动作={action}，检测到异常值 {outlier_count} 个")
        return self

    # ------------------------------------------------------------------
    # 3. 数据类型转换
    # ------------------------------------------------------------------
    def convert_types(self):
        """
        自动识别并转换列类型：
          - 金额列（含 $€£¥ 或千分位逗号）→ 数值型
          - 可解析为日期的列 → datetime
          - 纯数字字符串 → 数值型
        """
        df = self.df
        converted = []

        for col in df.columns:
            original_dtype = df[col].dtype

            # 金额列
            if self._is_money_series(df[col]):
                df[col] = df[col].apply(self._parse_money)
                converted.append(f"{col}: 金额→float")
                continue

            # 日期列
            if self._is_datetime_series(df[col]):
                df[col] = pd.to_datetime(df[col], errors="coerce", infer_datetime_format=True)
                converted.append(f"{col}: 文本→datetime")
                continue

            # 纯数字字符串（无单位、无符号）
            if df[col].dtype == "object":
                sample = df[col].dropna().astype(str).head(100)
                if not sample.empty:
                    cleaned = sample.str.replace(r"[,，\s]", "", regex=True)
                    num_converted = pd.to_numeric(cleaned, errors="coerce")
                    if num_converted.notna().mean() > 0.9:
                        df[col] = pd.to_numeric(
                            df[col].astype(str).str.replace(r"[,，\s]", "", regex=True),
                            errors="coerce",
                        )
                        converted.append(f"{col}: 文本→数值")

        self.df = df
        self._log("类型转换", f"共转换 {len(converted)} 列：{converted}")
        return self

    # ------------------------------------------------------------------
    # 4. 重复值处理
    # ------------------------------------------------------------------
    def handle_duplicates(self, subset=None, keep="first"):
        """
        检测并删除重复行。

        Parameters
        ----------
        subset : list or None
            指定判断重复的列，None 表示全部列
        keep : str
            'first' 保留首次出现，'last' 保留最后一次，False 全部删除
        """
        df = self.df
        before = len(df)
        dup_count = int(df.duplicated(subset=subset, keep=keep).sum())
        df = df.drop_duplicates(subset=subset, keep=keep).reset_index(drop=True)
        after = len(df)

        self.df = df
        self._log("去重", f"删除 {before - after} 行重复数据（检测到 {dup_count} 条重复）")
        return self

    # ------------------------------------------------------------------
    # 5. 文本清洗
    # ------------------------------------------------------------------
    def clean_text(self, case="lower", remove_special=True, strip=True, remove_extra_spaces=True):
        """
        清洗文本列（object/string 类型）。

        Parameters
        ----------
        case : str
            'lower' 全小写、'upper' 全大写、'title' 首字母大写、None 不处理
        remove_special : bool
            是否移除特殊字符（保留中文、英文、数字、空格）
        strip : bool
            是否去除首尾空格
        remove_extra_spaces : bool
            是否把连续空格压缩为单个
        """
        df = self.df
        text_cols = df.select_dtypes(include=["object", "string"]).columns.tolist()
        cleaned_cols = []

        for col in text_cols:
            s = df[col].astype("string")

            if strip:
                s = s.str.strip()
            if remove_extra_spaces:
                s = s.str.replace(r"\s+", " ", regex=True)
            if remove_special:
                # 仅保留中文、英文、数字、空格
                s = s.str.replace(r"[^\u4e00-\u9fa5A-Za-z0-9\s]", "", regex=True)
            if case == "lower":
                s = s.str.lower()
            elif case == "upper":
                s = s.str.upper()
            elif case == "title":
                s = s.str.title()

            df[col] = s
            cleaned_cols.append(col)

        self.df = df
        self._log("文本清洗",
                  f"清洗 {len(cleaned_cols)} 个文本列，case={case}，去特殊字符={remove_special}")
        return self

    # ------------------------------------------------------------------
    # 6. 一键清洗
    # ------------------------------------------------------------------
    def clean_all(self, missing_strategy="auto", outlier_method="iqr", outlier_action="mark"):
        """
        一键完成所有常规清洗步骤：
          1. 数据类型转换（金额、日期、数字）
          2. 文本清洗（去空格、统一大小写、去特殊字符）
          3. 重复值去重
          4. 缺失值处理
          5. 异常值处理

        Parameters
        ----------
        missing_strategy : str  缺失值策略（见 handle_missing）
        outlier_method : str    异常值检测方法（iqr / 3sigma）
        outlier_action : str    异常值处理动作（mark / remove / clip）
        """
        (self
         .convert_types()
         .clean_text()
         .handle_duplicates()
         .handle_missing(strategy=missing_strategy)
         .handle_outliers(method=outlier_method, action=outlier_action))

        self.report["最终行数"] = len(self.df)
        self.report["最终列数"] = self.df.shape[1]
        self._log("一键清洗完成", "类型转换→文本清洗→去重→缺失值→异常值")
        return self


# ----------------------------------------------------------------------
# 便捷函数（不使用类的快捷方式）
# ----------------------------------------------------------------------
def clean_dataframe(df, **kwargs):
    """一键清洗 DataFrame，返回 (清洗后df, 报告字典)。"""
    cleaner = DataCleaner(df).clean_all(**kwargs)
    return cleaner.get_data(), cleaner.get_report()


if __name__ == "__main__":
    # 自测
    demo = pd.DataFrame({
        "姓名": [" 张三 ", "李四", "王五", "赵六", "钱七", "孙八", "张三", None],
        "年龄": [28, 32, 25, 41, 29, 350, 28, 30],
        "薪资": ["$1,500.00", "$2,200.50", None, "$3,500", "$1,800", "$2,600", "$1,500.00", "$2,000"],
        "城市": ["北京", "上海", "深圳", "北京", "广州", None, "北京", "上海"],
        "入职日期": ["2021-03-15", "2019-07-01", "2022-01-10", "2015-11-20",
                    "2020-05-08", "2018-09-12", "2021-03-15", "2021-06-01"],
        "备注": ["优秀!!!", "良好", None, "优秀", "一般@@", "良好", "优秀!!!", "良好"],
    })

    print("原始数据：")
    print(demo)
    print("\n" + "=" * 60)

    cleaner = DataCleaner(demo).clean_all()
    df_clean = cleaner.get_data()

    print("\n清洗后数据：")
    print(df_clean.to_string())
    print("\n清洗报告：")
    for k, v in cleaner.get_report().items():
        print(f"  {k}: {v}")
