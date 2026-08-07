# -*- coding: utf-8 -*-
"""
==============================================================
  data_utils.py — 数据层（CRUD / 图片 / 判定 / 报告 / 通知）
  物理实验室 · 渗层检测工作台 v3.0
  兼容 Python 3.9 | streamlit==1.37.1 | pandas==2.2.3
==============================================================
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
import io

import pandas as pd
import streamlit as st

from config import (
    INSPECTION_STANDARDS,
    IMAGE_CATEGORIES,
    RANGE_ALERT_THRESHOLDS,
    STATUS_PENDING,
    STATUS_IN_PROGRESS,
    STATUS_COMPLETED,
)


# ──────────────────────────────────────────────
#  工具函数
# ──────────────────────────────────────────────
def _uid():
    # type: () -> str
    return uuid.uuid4().hex[:8].upper()


def _now():
    # type: () -> str
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ──────────────────────────────────────────────
#  初始化
# ──────────────────────────────────────────────
def init_session_state():
    # type: () -> None
    if "_lab_init" not in st.session_state:
        st.session_state._lab_init = True
        st.session_state.trays = []          # type: List[Dict[str, Any]]
        st.session_state.current_tray_id = None  # type: Optional[str]
        ensure_demo_data()


def ensure_demo_data():
    # type: () -> None
    """预置演示数据：至少 2 个料盘号，覆盖 6 大检测项目"""
    if st.session_state.trays:
        return

    # ---------- 料盘 1：全部合格 ----------
    tray_ok = _make_tray(
        tray_id="LP-2026-001",
        product_model="型号A",
        material_grade="20CrMnTi",
        work_order="WO-20260801-001",
    )
    tray_ok["status"] = STATUS_COMPLETED
    tray_ok["inspection"] = {
        "chd_values": [1.05, 1.08, 1.02],
        "chd_mean": 1.05, "chd_range": 0.06,
        "surface_hardness_values": [61.5, 62.0, 61.0],
        "surface_hardness_mean": 61.5, "surface_hardness_range": 1.0,
        "core_hardness_values": [38.0, 37.5, 38.5],
        "core_hardness_mean": 38.0, "core_hardness_range": 1.0,
        "surface_carbon": 0.82,
        "retained_austenite": 5.5,
        "metallographic_grade": 2,
        "carbide_result": "合格",
        "judgment": "pass",
        "alert_level": "normal",
        "nok_items": [],
        "completed_at": "2026-08-01 10:30:00",
    }
    tray_ok["images"] = []

    # ---------- 料盘 2：碳化物不合格 → 红色预警 ----------
    tray_ng = _make_tray(
        tray_id="LP-2026-002",
        product_model="型号B",
        material_grade="18CrNiMo7-6",
        work_order="WO-20260802-002",
    )
    tray_ng["status"] = STATUS_COMPLETED
    tray_ng["inspection"] = {
        "chd_values": [1.35, 1.30, 1.32],
        "chd_mean": 1.32, "chd_range": 0.05,
        "surface_hardness_values": [60.0, 59.5, 60.5],
        "surface_hardness_mean": 60.0, "surface_hardness_range": 1.0,
        "core_hardness_values": [35.0, 34.5, 35.5],
        "core_hardness_mean": 35.0, "core_hardness_range": 1.0,
        "surface_carbon": 0.78,
        "retained_austenite": 6.2,
        "metallographic_grade": 2,
        "carbide_result": "不合格",
        "judgment": "fail",
        "alert_level": "critical",
        "nok_items": [
            {
                "item": "碳化物形态",
                "measured": "不合格（网状碳化物）",
                "standard": "合格",
                "deviation": "定性不合格",
                "time": "2026-08-02 14:20:00",
            }
        ],
        "completed_at": "2026-08-02 14:20:00",
    }
    tray_ng["images"] = []

    # ---------- 料盘 3：待检测（用于扫码演示） ----------
    tray_wait = _make_tray(
        tray_id="LP-2026-003",
        product_model="型号A",
        material_grade="20CrMnTi",
        work_order="WO-20260803-003",
    )
    tray_wait["status"] = STATUS_PENDING
    tray_wait["inspection"] = None
    tray_wait["images"] = []

    st.session_state.trays = [tray_ok, tray_ng, tray_wait]


def _make_tray(tray_id, product_model, material_grade, work_order):
    # type: (str, str, str, str) -> Dict[str, Any]
    return {
        "tray_id": tray_id,
        "product_model": product_model,
        "material_grade": material_grade,
        "work_order": work_order,
        "status": STATUS_PENDING,
        "inspection": None,
        "images": [],
        "created_at": _now(),
    }


# ──────────────────────────────────────────────
#  料盘 CRUD
# ──────────────────────────────────────────────
def create_tray(tray_id, product_model, material_grade, work_order):
    # type: (str, str, str, str) -> Dict[str, Any]
    tray = _make_tray(tray_id, product_model, material_grade, work_order)
    st.session_state.trays.append(tray)
    return tray


def get_tray(tray_id):
    # type: (str) -> Optional[Dict[str, Any]]
    for t in st.session_state.trays:
        if t["tray_id"] == tray_id:
            return t
    return None


def get_all_trays():
    # type: () -> List[Dict[str, Any]]
    return st.session_state.trays


# ──────────────────────────────────────────────
#  检测记录 + 自动判定
# ──────────────────────────────────────────────
def add_inspection_record(tray_id, data):
    # type: (str, Dict[str, Any]) -> Dict[str, Any]
    """
    录入 6 大检测项目并自动判定。
    data 字段:
      chd_values, surface_hardness_values, core_hardness_values,
      surface_carbon, retained_austenite,
      metallographic_grade, carbide_result
    """
    tray = get_tray(tray_id)
    if tray is None:
        return {"error": "料盘号不存在"}

    model = tray["product_model"]
    std = INSPECTION_STANDARDS.get(model, {})
    nok_items = []  # type: List[Dict[str, str]]

    # --- 三点测量均值 / 极差 ---
    for key in ("chd", "surface_hardness", "core_hardness"):
        vals = data.get(key + "_values", [])
        if vals:
            data[key + "_mean"] = round(sum(vals) / len(vals), 3)
            data[key + "_range"] = round(max(vals) - min(vals), 3)
        else:
            data[key + "_mean"] = 0.0
            data[key + "_range"] = 0.0

    # --- 逐项判定 ---
    def _check(key, measured):
        # type: (str, float) -> None
        spec = std.get(key)
        if spec is None or spec.get("input_type") == "qualitative":
            return
        usl = spec.get("usl")
        lsl = spec.get("lsl")
        if usl is not None and lsl is not None:
            if measured > usl or measured < lsl:
                nok_items.append({
                    "item": spec["name"],
                    "measured": str(measured) + " " + spec.get("unit", ""),
                    "standard": "{}~{} {}".format(lsl, usl, spec.get("unit", "")),
                    "deviation": "{:+.3f}".format(
                        measured - usl if measured > usl else measured - lsl
                    ),
                    "time": _now(),
                })

    _check("chd", data.get("chd_mean", 0))
    _check("surface_hardness", data.get("surface_hardness_mean", 0))
    _check("core_hardness", data.get("core_hardness_mean", 0))
    _check("surface_carbon", data.get("surface_carbon", 0))
    _check("retained_austenite", data.get("retained_austenite", 0))
    _check("metallographic", data.get("metallographic_grade", 0))

    # --- 碳化物定性判定 ---
    carbide = data.get("carbide_result", "合格")
    if carbide == "不合格":
        nok_items.append({
            "item": "碳化物形态",
            "measured": "不合格",
            "standard": "合格",
            "deviation": "定性不合格",
            "time": _now(),
        })

    # --- 综合判定 ---
    has_critical = (carbide == "不合格")
    if has_critical:
        judgment = "fail"
        alert_level = "critical"
    elif nok_items:
        judgment = "fail"
        alert_level = "warning"
    else:
        judgment = "pass"
        alert_level = "normal"

    data["judgment"] = judgment
    data["alert_level"] = alert_level
    data["nok_items"] = nok_items
    data["completed_at"] = _now()

    tray["inspection"] = data
    tray["status"] = STATUS_COMPLETED
    return data


# ──────────────────────────────────────────────
#  图片 CRUD
# ──────────────────────────────────────────────
def add_image(tray_id, category, file_name, file_bytes, embed_in_report=True):
    # type: (str, str, str, bytes, bool) -> None
    tray = get_tray(tray_id)
    if tray is None:
        return
    tray.setdefault("images", []).append({
        "id": _uid(),
        "category": category,
        "file_name": file_name,
        "data": file_bytes,
        "embed_in_report": embed_in_report,
        "uploaded_at": _now(),
    })


def get_images(tray_id, category=None):
    # type: (str, Optional[str]) -> List[Dict[str, Any]]
    tray = get_tray(tray_id)
    if tray is None:
        return []
    imgs = tray.get("images", [])
    if category:
        imgs = [i for i in imgs if i.get("category") == category]
    return imgs


# ──────────────────────────────────────────────
#  不合格清单
# ──────────────────────────────────────────────
def generate_nok_list():
    # type: () -> pd.DataFrame
    rows = []  # type: List[Dict[str, str]]
    for tray in st.session_state.trays:
        insp = tray.get("inspection")
        if insp is None:
            continue
        for nok in insp.get("nok_items", []):
            rows.append({
                "料盘号": tray["tray_id"],
                "产品型号": tray["product_model"],
                "不合格项目": nok.get("item", ""),
                "实测值": nok.get("measured", ""),
                "标准值": nok.get("standard", ""),
                "偏差": nok.get("deviation", ""),
                "判定时间": nok.get("time", ""),
            })
    if not rows:
        return pd.DataFrame(
            columns=["料盘号", "产品型号", "不合格项目",
                     "实测值", "标准值", "偏差", "判定时间"]
        )
    return pd.DataFrame(rows)


# ──────────────────────────────────────────────
#  HTML 报告生成
# ──────────────────────────────────────────────
def generate_report(tray_id):
    # type: (str) -> str
    tray = get_tray(tray_id)
    if tray is None:
        return "<p>料盘号不存在</p>"

    insp = tray.get("inspection") or {}
    judgment = insp.get("judgment", "pending")
    nok_items = insp.get("nok_items", [])
    std = INSPECTION_STANDARDS.get(tray["product_model"], {})

    # 智能结论
    if judgment == "pass":
        conclusion_color = "#28a745"
        conclusion_text = "该批次渗层检测合格，可放行，流转至磨削工序。"
    else:
        conclusion_color = "#dc3545"
        names = "、".join(list(dict.fromkeys(
            [n["item"] for n in nok_items]
        )))
        conclusion_text = (
            "该批次因【{}】不合格，建议报废/返工，详见不合格清单。".format(names)
        )

    # 图片（仅嵌入报告）
    embed_imgs = [
        img for img in tray.get("images", [])
        if img.get("embed_in_report", False)
    ]
    img_html = ""
    for img in embed_imgs:
        cat_name = IMAGE_CATEGORIES.get(img.get("category", "other"), "其他")
        img_html += (
            '<div style="display:inline-block;margin:8px;text-align:center;">'
            '<img src="data:image/png;base64,{b64}" width="180"/>'
            '<br/><small>{cat} - {fn}</small></div>'
        ).format(
            b64=_bytes_to_b64(img.get("data", b"")),
            cat=cat_name,
            fn=img.get("file_name", ""),
        )

    # 数据表格行
    def _row(label, key, unit=""):
        spec = std.get(key, {})
        val = insp.get(key, "—")
        if key in ("chd", "surface_hardness", "core_hardness"):
            val = insp.get(key + "_mean", "—")
            rng = insp.get(key + "_range", "—")
            return "<tr><td>{}</td><td>{} {}</td><td>极差 {}</td>" \
                   "<td>{}~{} {}</td></tr>".format(
                       label, val, unit, rng,
                       spec.get("lsl", "—"), spec.get("usl", "—"), unit)
        return "<tr><td>{}</td><td>{} {}</td><td>—</td>" \
               "<td>{}~{} {}</td></tr>".format(
                   label, val, unit,
                   spec.get("lsl", "—"), spec.get("usl", "—"), unit)

    html = """
<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  body{{font-family:'Microsoft YaHei',sans-serif;margin:30px;color:#333;}}
  h1{{text-align:center;color:#1a5276;}}
  h2{{color:#2c3e50;border-bottom:2px solid #2c3e50;padding-bottom:4px;}}
  table{{border-collapse:collapse;width:100%;margin:10px 0;}}
  th,td{{border:1px solid #ccc;padding:8px 12px;text-align:center;}}
  th{{background:#2c3e50;color:#fff;}}
  .conclusion{{font-size:22px;font-weight:bold;color:{cc};
               text-align:center;margin:20px 0;padding:15px;
               border:2px solid {cc};border-radius:8px;}}
  .nok-table td{{color:#dc3545;font-weight:bold;}}
  .footer{{text-align:center;color:#999;font-size:12px;margin-top:30px;}}
</style></head><body>
<h1>🔬 渗层检测报告</h1>
<p style="text-align:center;color:#666;">
  料盘号：<b>{tid}</b> ｜ 产品型号：{pm} ｜ 材料牌号：{mg}<br/>
  工单号：{wo} ｜ 检测时间：{ct}
</p>
<div class="conclusion">{concl}</div>

<h2>一、检测数据</h2>
<table>
<tr><th>检测项目</th><th>实测值</th><th>极差</th><th>标准范围</th></tr>
{rows}
<tr><td>碳化物形态</td><td>{carb}</td><td>—</td><td>合格</td></tr>
</table>

<h2>二、不合格清单</h2>
{nok_section}

<h2>三、检测图片</h2>
<div>{imgs}</div>

<div class="footer">
  报告生成时间：{gen_time} ｜ 物理实验室数据采集与过程控制系统 v3.0
</div>
</body></html>
""".format(
        tid=tray["tray_id"],
        pm=tray["product_model"],
        mg=tray.get("material_grade", ""),
        wo=tray.get("work_order", ""),
        ct=insp.get("completed_at", _now()),
        cc=conclusion_color,
        concl=conclusion_text,
        rows=(
            _row("有效硬化层深度(CHD)", "chd", "mm")
            + _row("表面硬度", "surface_hardness", "HRC")
            + _row("心部硬度", "core_hardness", "HRC")
            + _row("表面碳含量", "surface_carbon", "%")
            + _row("残余奥氏体", "retained_austenite", "%")
            + _row("金相组织评级", "metallographic", "级")
        ),
        carb=insp.get("carbide_result", "—"),
        nok_section=_nok_html(nok_items),
        imgs=img_html if img_html else "<p>无嵌入图片</p>",
        gen_time=_now(),
    )
    return html


def _nok_html(nok_items):
    # type: (List[Dict[str, str]]) -> str
    if not nok_items:
        return '<p style="color:#28a745;font-weight:bold;">✅ 无不合格项</p>'
    rows = ""
    for n in nok_items:
        rows += "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
            n.get("item", ""), n.get("measured", ""),
            n.get("standard", ""), n.get("deviation", ""),
            n.get("time", ""),
        )
    return (
        '<table class="nok-table">'
        "<tr><th>项目</th><th>实测值</th><th>标准值</th>"
        "<th>偏差</th><th>时间</th></tr>"
        + rows + "</table>"
    )


def _bytes_to_b64(data):
    # type: (bytes) -> str
    import base64
    if not data:
        return ""
    return base64.b64encode(data).decode("utf-8")


# ──────────────────────────────────────────────
#  通知 QE（预留企业微信接口）
# ──────────────────────────────────────────────
def generate_notification(tray_id):
    # type: (str) -> str
    """
    生成网页内通知内容。
    TODO: 预留企业微信推送接口
      - 对接时替换 _push_to_wecom() 内部实现即可
    """
    tray = get_tray(tray_id)
    if tray is None:
        return "料盘号不存在"
    insp = tray.get("inspection") or {}
    nok_items = insp.get("nok_items", [])

    if not nok_items:
        return "✅ 料盘 {} 全部合格，无需通知。".format(tray_id)

    lines = [
        "🚨 【渗层检测不合格通知】",
        "料盘号：{}".format(tray_id),
        "产品型号：{}".format(tray["product_model"]),
        "工单号：{}".format(tray.get("work_order", "")),
        "检测时间：{}".format(insp.get("completed_at", "")),
        "",
        "不合格项目：",
    ]
    for i, n in enumerate(nok_items, 1):
        lines.append("  {}. {} | 实测: {} | 标准: {}".format(
            i, n.get("item"), n.get("measured"), n.get("standard")))

    alert = insp.get("alert_level", "warning")
    if alert == "critical":
        lines.append("")
        lines.append("⚠️ 红色预警：存在严重不合格项，请立即处理！")
        lines.append("处理建议：隔离该批次产品，通知工艺工程师评审，"
                      "决定是否报废或返工。")
    else:
        lines.append("")
        lines.append("⚡ 黄色预警：存在超差项，请复检确认。")
        lines.append("处理建议：对该批次进行复检，确认是否为测量误差。")

    lines.append("")
    lines.append("—— 系统自动发送 · 物理实验室 v3.0")
    return "\n".join(lines)


def _push_to_wecom(message):
    # type: (str) -> None
    """
    预留企业微信推送接口。
    当前阶段仅在网页内展示，待 IT 支持后对接 Webhook。
    """
    pass  # TODO: requests.post(WECOM_WEBHOOK_URL, json={"msgtype":"text","text":{"content":message}})


# ──────────────────────────────────────────────
#  成分文件解析（CSV / ESG）
# ──────────────────────────────────────────────
def parse_composition_file(uploaded_file):
    # type: (Any) -> Optional[float]
    """
    解析光谱仪/残奥仪导出的 CSV 或 ESG 文件，
    提取第一个可识别的浮点数值。
    """
    try:
        raw = uploaded_file.read()
        text = raw.decode("utf-8", errors="ignore")
        for line in text.strip().splitlines():
            parts = line.replace(";", ",").split(",")
            for p in parts:
                p = p.strip()
                try:
                    return float(p)
                except ValueError:
                    continue
    except Exception:
        pass
    return None