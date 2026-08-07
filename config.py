# -*- coding: utf-8 -*-
"""
==============================================================
  config.py — 纯配置层（无业务逻辑）
  物理实验室 · 渗层检测工作台 v3.0
  兼容 Python 3.9 | streamlit==1.37.1
==============================================================
"""
from typing import Dict, List, Any, Optional

# ============================================================
#  产品型号列表
# ============================================================
PRODUCT_MODELS = ["型号A", "型号B", "型号C"]  # type: List[str]

# ============================================================
#  6 大渗层检测项目判定标准（按产品型号区分）
#  每项包含: name / unit / usl / lsl / target / input_type
#  input_type: "numeric"=数值录入  "qualitative"=定性判定
# ============================================================
INSPECTION_STANDARDS = {
    "型号A": {
        "chd": {
            "name": "有效硬化层深度(CHD)",
            "unit": "mm",
            "usl": 1.2,
            "lsl": 0.8,
            "target": 1.0,
            "input_type": "numeric",
            "points": 3,          # 三点测量
        },
        "surface_hardness": {
            "name": "表面硬度",
            "unit": "HRC",
            "usl": 65,
            "lsl": 58,
            "target": 61,
            "input_type": "numeric",
            "points": 3,
        },
        "core_hardness": {
            "name": "心部硬度",
            "unit": "HRC",
            "usl": 45,
            "lsl": 30,
            "target": 38,
            "input_type": "numeric",
            "points": 3,
        },
        "surface_carbon": {
            "name": "表面碳含量",
            "unit": "%",
            "usl": 0.95,
            "lsl": 0.70,
            "target": 0.82,
            "input_type": "numeric",
            "points": 1,
        },
        "retained_austenite": {
            "name": "残余奥氏体含量",
            "unit": "%",
            "usl": 8.0,
            "lsl": 0.0,
            "target": 5.0,
            "input_type": "numeric",
            "points": 1,
        },
        "metallographic": {
            "name": "金相组织评级",
            "unit": "级",
            "usl": 3,
            "lsl": 1,
            "target": 2,
            "input_type": "numeric",
            "points": 1,
        },
        "carbide": {
            "name": "碳化物形态",
            "unit": "",
            "usl": None,
            "lsl": None,
            "target": None,
            "input_type": "qualitative",   # 合格 / 不合格
            "points": 1,
        },
    },
    "型号B": {
        "chd": {
            "name": "有效硬化层深度(CHD)",
            "unit": "mm",
            "usl": 1.6,
            "lsl": 1.0,
            "target": 1.3,
            "input_type": "numeric",
            "points": 3,
        },
        "surface_hardness": {
            "name": "表面硬度",
            "unit": "HRC",
            "usl": 64,
            "lsl": 56,
            "target": 60,
            "input_type": "numeric",
            "points": 3,
        },
        "core_hardness": {
            "name": "心部硬度",
            "unit": "HRC",
            "usl": 42,
            "lsl": 28,
            "target": 35,
            "input_type": "numeric",
            "points": 3,
        },
        "surface_carbon": {
            "name": "表面碳含量",
            "unit": "%",
            "usl": 0.85,
            "lsl": 0.65,
            "target": 0.75,
            "input_type": "numeric",
            "points": 1,
        },
        "retained_austenite": {
            "name": "残余奥氏体含量",
            "unit": "%",
            "usl": 10.0,
            "lsl": 0.0,
            "target": 6.0,
            "input_type": "numeric",
            "points": 1,
        },
        "metallographic": {
            "name": "金相组织评级",
            "unit": "级",
            "usl": 3,
            "lsl": 1,
            "target": 2,
            "input_type": "numeric",
            "points": 1,
        },
        "carbide": {
            "name": "碳化物形态",
            "unit": "",
            "usl": None,
            "lsl": None,
            "target": None,
            "input_type": "qualitative",
            "points": 1,
        },
    },
    "型号C": {
        "chd": {
            "name": "有效硬化层深度(CHD)",
            "unit": "mm",
            "usl": 1.0,
            "lsl": 0.6,
            "target": 0.8,
            "input_type": "numeric",
            "points": 3,
        },
        "surface_hardness": {
            "name": "表面硬度",
            "unit": "HRC",
            "usl": 66,
            "lsl": 60,
            "target": 63,
            "input_type": "numeric",
            "points": 3,
        },
        "core_hardness": {
            "name": "心部硬度",
            "unit": "HRC",
            "usl": 48,
            "lsl": 32,
            "target": 40,
            "input_type": "numeric",
            "points": 3,
        },
        "surface_carbon": {
            "name": "表面碳含量",
            "unit": "%",
            "usl": 0.95,
            "lsl": 0.75,
            "target": 0.85,
            "input_type": "numeric",
            "points": 1,
        },
        "retained_austenite": {
            "name": "残余奥氏体含量",
            "unit": "%",
            "usl": 6.0,
            "lsl": 0.0,
            "target": 3.0,
            "input_type": "numeric",
            "points": 1,
        },
        "metallographic": {
            "name": "金相组织评级",
            "unit": "级",
            "usl": 2,
            "lsl": 1,
            "target": 1,
            "input_type": "numeric",
            "points": 1,
        },
        "carbide": {
            "name": "碳化物形态",
            "unit": "",
            "usl": None,
            "lsl": None,
            "target": None,
            "input_type": "qualitative",
            "points": 1,
        },
    },
}  # type: Dict[str, Dict[str, Dict[str, Any]]]

# ============================================================
#  图片分类（保持不变）
# ============================================================
IMAGE_CATEGORIES = {
    "metallographic": "金相图",
    "spectrum":       "光谱图",
    "retained_aust":  "残奥图",
    "hardness":       "硬度图",
    "carbide":        "碳化物图",
    "other":          "其他",
}  # type: Dict[str, str]

# ============================================================
#  SPC 常数（保持不变）
# ============================================================
SPC_E2 = 2.660       # I 图控制限系数 (n=2)
SPC_D4 = 3.267       # MR 图上控制限系数
SPC_D3 = 0.0         # MR 图下控制限系数
SPC_MIN_POINTS = 5   # 最少数据点数

# ============================================================
#  极差复检阈值（极差 > 该值时提示"建议复检"）
# ============================================================
RANGE_ALERT_THRESHOLDS = {
    "chd": 0.15,               # mm
    "surface_hardness": 3.0,   # HRC
    "core_hardness": 3.0,      # HRC
}  # type: Dict[str, float]

# ============================================================
#  料盘状态
# ============================================================
STATUS_PENDING     = "待检测"
STATUS_IN_PROGRESS = "检测中"
STATUS_COMPLETED   = "已完成"