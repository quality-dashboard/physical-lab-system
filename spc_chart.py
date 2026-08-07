# -*- coding: utf-8 -*-
"""
==============================================================
  spc_chart.py — SPC 层（I-MR 控制图计算 + Plotly 渲染）
  物理实验室 · 渗层检测工作台 v3.0
  兼容 Python 3.9 | plotly==5.24.1 | pandas==2.2.3
==============================================================
"""
from typing import List, Dict, Any, Optional, Tuple

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import SPC_E2, SPC_D4, SPC_D3, SPC_MIN_POINTS


# ──────────────────────────────────────────────
#  I-MR 控制限计算
# ──────────────────────────────────────────────
def calculate_imr(values):
    # type: (List[float]) -> Dict[str, Any]
    """
    计算单值-移动极差 (I-MR) 控制限。
    返回 dict 包含:
      i_mean, i_ucl, i_lcl,
      mr_mean, mr_ucl, mr_lcl,
      outliers_i, outliers_mr
    """
    n = len(values)
    if n < 2:
        return {"error": "数据不足"}

    s = pd.Series(values)

    # I 图
    i_mean = float(s.mean())
    # 移动极差
    mr = s.diff().abs().dropna().tolist()  # type: List[float]
    mr_mean = float(sum(mr) / len(mr)) if mr else 0.0

    i_ucl = i_mean + SPC_E2 * mr_mean
    i_lcl = i_mean - SPC_E2 * mr_mean

    # MR 图
    mr_ucl = SPC_D4 * mr_mean
    mr_lcl = SPC_D3 * mr_mean

    # 异常点
    outliers_i = [
        idx for idx, v in enumerate(values)
        if v > i_ucl or v < i_lcl
    ]
    outliers_mr = [
        idx for idx, v in enumerate(mr)
        if v > mr_ucl or v < mr_lcl
    ]

    return {
        "i_mean": i_mean, "i_ucl": i_ucl, "i_lcl": i_lcl,
        "mr_mean": mr_mean, "mr_ucl": mr_ucl, "mr_lcl": mr_lcl,
        "outliers_i": outliers_i, "outliers_mr": outliers_mr,
        "values": values, "mr_values": mr,
    }


# ──────────────────────────────────────────────
#  I 图渲染
# ──────────────────────────────────────────────
def render_i_chart(imr, title="I 图（单值）"):
    # type: (Dict[str, Any], str) -> None
    if "error" in imr:
        st.info("数据不足，无法生成 I 图。")
        return

    vals = imr["values"]
    fig = go.Figure()

    # 数据点
    colors = [
        "red" if i in imr["outliers_i"] else "#1f77b4"
        for i in range(len(vals))
    ]
    fig.add_trace(go.Scatter(
        y=vals, mode="lines+markers", name="实测值",
        line=dict(color="#1f77b4", width=1.5),
        marker=dict(size=7, color=colors),
    ))

    # 控制限
    fig.add_hline(y=imr["i_mean"], line_color="green",
                  annotation_text="CL={:.3f}".format(imr["i_mean"]))
    fig.add_hline(y=imr["i_ucl"], line_dash="dash", line_color="red",
                  annotation_text="UCL={:.3f}".format(imr["i_ucl"]))
    fig.add_hline(y=imr["i_lcl"], line_dash="dash", line_color="red",
                  annotation_text="LCL={:.3f}".format(imr["i_lcl"]))

    fig.update_layout(
        title=title, xaxis_title="序号", yaxis_title="值",
        height=320, margin=dict(l=50, r=20, t=50, b=40),
    )
    st.plotly_chart(fig, use_container_width=True)


# ──────────────────────────────────────────────
#  MR 图渲染
# ──────────────────────────────────────────────
def render_mr_chart(imr, title="MR 图（移动极差）"):
    # type: (Dict[str, Any], str) -> None
    if "error" in imr:
        return

    mr = imr["mr_values"]
    if not mr:
        return

    fig = go.Figure()
    colors = [
        "red" if i in imr["outliers_mr"] else "#ff7f0e"
        for i in range(len(mr))
    ]
    fig.add_trace(go.Scatter(
        y=mr, mode="lines+markers", name="移动极差",
        line=dict(color="#ff7f0e", width=1.5),
        marker=dict(size=7, color=colors),
    ))

    fig.add_hline(y=imr["mr_mean"], line_color="green",
                  annotation_text="CL={:.3f}".format(imr["mr_mean"]))
    fig.add_hline(y=imr["mr_ucl"], line_dash="dash", line_color="red",
                  annotation_text="UCL={:.3f}".format(imr["mr_ucl"]))
    fig.add_hline(y=imr["mr_lcl"], line_dash="dash", line_color="red",
                  annotation_text="LCL={:.3f}".format(imr["mr_lcl"]))

    fig.update_layout(
        title=title, xaxis_title="序号", yaxis_title="极差",
        height=320, margin=dict(l=50, r=20, t=50, b=40),
    )
    st.plotly_chart(fig, use_container_width=True)


# ──────────────────────────────────────────────
#  完整 SPC 面板（对 6 大关键指标）
# ──────────────────────────────────────────────
def render_spc_panel(trays):
    # type: (List[Dict[str, Any]]) -> None
    """从所有已完成料盘中提取数据，绘制 I-MR 图"""
    metrics = [
        ("chd_mean", "CHD 均值 (mm)"),
        ("surface_hardness_mean", "表面硬度均值 (HRC)"),
        ("core_hardness_mean", "心部硬度均值 (HRC)"),
        ("surface_carbon", "表面碳含量 (%)"),
        ("retained_austenite", "残余奥氏体 (%)"),
    ]

    # 收集数据
    data_map = {}  # type: Dict[str, List[float]]
    for key, _ in metrics:
        data_map[key] = []
    for tray in trays:
        insp = tray.get("inspection")
        if insp is None:
            continue
        for key, _ in metrics:
            v = insp.get(key)
            if v is not None:
                data_map[key].append(float(v))

    if not any(data_map.values()):
        st.info("暂无已完成的检测数据，无法生成 SPC 图。")
        return

    col_l, col_r = st.columns(2)
    for i, (key, label) in enumerate(metrics):
        vals = data_map[key]
        if len(vals) < SPC_MIN_POINTS:
            with (col_l if i % 2 == 0 else col_r):
                st.info("「{}」数据点不足（需≥{}个），暂无法生成控制图。".format(
                    label, SPC_MIN_POINTS))
            continue
        imr = calculate_imr(vals)
        with (col_l if i % 2 == 0 else col_r):
            render_i_chart(imr, title="I 图 — " + label)
            render_mr_chart(imr, title="MR 图 — " + label)