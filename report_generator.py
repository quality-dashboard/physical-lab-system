# -*- coding: utf-8 -*-
"""
报告生成模块
依赖: streamlit==1.37.1
"""
from typing import Dict, Any, List
from datetime import datetime

import streamlit as st

from config import JUDGMENT_MAP, ALERT_LEVEL_MAP, IMAGE_CATEGORIES


def generate_report(record: Dict[str, Any]) -> str:
    """生成单条检测记录的文本报告"""
    judgment_text = JUDGMENT_MAP.get(record.get("overall_judgment", "pending"), "⏳ 待检")
    alert_text = ALERT_LEVEL_MAP.get(record.get("alert_level", "normal"), "正常")

    lines = [
        "=" * 60,
        "        物理实验室 · 检测报告",
        "=" * 60,
        "",
        f"报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"记录编号：{record.get('id', 'N/A')}",
        f"料盘号：{record.get('tray_number', 'N/A')}",
        f"产品型号：{record.get('product_name', 'N/A')}",
        f"检测时间：{record.get('created_at', 'N/A')}",
        "",
        "-" * 60,
        "一、检测数据",
        "-" * 60,
        f"  渗层深度 (CHD)：{record.get('chd_mm', 'N/A')} mm",
        f"  表面碳含量：{record.get('surface_carbon_pct', 'N/A')} %C",
        f"  残余奥氏体：{record.get('retained_austenite_pct', 'N/A')} %",
        f"  金相级别：{record.get('metallographic_grade', 'N/A')} 级",
        f"  表面硬度：{record.get('surface_hardness', 'N/A')} HRC",
        f"  心部硬度：{record.get('core_hardness', 'N/A')} HRC",
        f"  碳化物检测：{record.get('carbide_result', 'N/A')}",
        "",
        "-" * 60,
        "二、综合判定",
        "-" * 60,
        f"  判定结果：{judgment_text}",
        f"  预警等级：{alert_text}",
        "",
    ]

    # 不合格原因
    details = record.get("judgment_details", [])
    if details:
        lines.append("  不合格/预警原因：")
        for i, d in enumerate(details, 1):
            lines.append(f"    {i}. {d}")
        lines.append("")

    # 图片信息
    images = record.get("images", [])
    embed_images = [img for img in images if img.get("embed_in_report", False)]
    if embed_images:
        lines.append("-" * 60)
        lines.append("三、嵌入报告的图片")
        lines.append("-" * 60)
        for img in embed_images:
            cat_name = IMAGE_CATEGORIES.get(img.get("category", "other"), "其他")
            lines.append(f"  [{cat_name}] {img.get('file_name', 'unknown')}")
        lines.append("")

    lines.append("=" * 60)
    lines.append("        报告结束")
    lines.append("=" * 60)

    return "\n".join(lines)


def render_report_section(record: Dict[str, Any]):
    """渲染报告生成区域"""
    st.subheader("📋 检测报告")

    if st.button("🔨 一键生成报告", key=f"gen_report_{record['id']}"):
        report_text = generate_report(record)
        st.session_state[f"report_{record['id']}"] = report_text
        st.success("报告已生成！")

    report_key = f"report_{record['id']}"
    if report_key in st.session_state:
        st.text_area("报告预览", st.session_state[report_key], height=400,
                     key=f"report_view_{record['id']}")

        file_name = f"报告_{record.get('tray_number', 'unknown')}_{datetime.now().strftime('%Y%m%d')}.txt"
        st.download_button(
            label="📥 下载报告 (.txt)",
            data=st.session_state[report_key],
            file_name=file_name,
            mime="text/plain",
            key=f"dl_report_{record['id']}",
        )