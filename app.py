# -*- coding: utf-8 -*-
"""
==============================================================
  app.py — 主入口（UI 渲染 + 页面路由）
  物理实验室 · 渗层检测工作台 v3.0
  依赖: streamlit==1.37.1  pandas==2.2.3  plotly==5.24.1
  启动: streamlit run app.py
==============================================================
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
import io

import streamlit as st
import pandas as pd

from config import (
    INSPECTION_STANDARDS,
    IMAGE_CATEGORIES,
    RANGE_ALERT_THRESHOLDS,
    STATUS_PENDING,
    STATUS_IN_PROGRESS,
    STATUS_COMPLETED,
)
from data_utils import (
    init_session_state,
    get_tray,
    get_all_trays,
    create_tray,
    add_inspection_record,
    add_image,
    get_images,
    generate_report,
    generate_nok_list,
    generate_notification,
    parse_composition_file,
)
from spc_chart import render_spc_panel

# ============================================================
#  页面配置
# ============================================================
st.set_page_config(
    page_title="渗层检测工作台 v3.0",
    page_icon="🔬",
    layout="wide",
)

# 初始化数据
init_session_state()

# ============================================================
#  注入全局 CSS（红色闪烁边框 + 预警条）
# ============================================================
st.markdown("""
<style>
@keyframes flashRed {
    0%,100%{ border-color:#dc3545; box-shadow:0 0 12px rgba(220,53,69,.6); }
    50%    { border-color:transparent; box-shadow:none; }
}
.carbide-alert {
    border: 3px solid #dc3545;
    border-radius: 10px;
    padding: 16px;
    animation: flashRed 1s infinite;
}
.alert-bar {
    background:#dc3545; color:#fff; text-align:center;
    font-size:20px; font-weight:bold; padding:12px;
    border-radius:8px; margin-bottom:16px;
}
.status-card {
    border-radius:10px; padding:18px; text-align:center;
    font-size:28px; font-weight:bold; color:#fff;
}
</style>
""", unsafe_allow_html=True)

# ============================================================
#  侧边栏导航
# ============================================================
st.sidebar.title("🔬 渗层检测工作台")
page = st.sidebar.radio(
    "功能导航",
    ["① 检测任务接收",
     "② 渗层检测工作台",
     "③ 报告与判定结果",
     "④ SPC 过程控制"],
    index=0,
)


# ============================================================
#  视图一：检测任务接收
# ============================================================
def view_task_reception():
    st.header("① 检测任务接收")

    trays = get_all_trays()

    # ---- 三色状态卡片 ----
    cnt_pending  = sum(1 for t in trays if t["status"] == STATUS_PENDING)
    cnt_progress = sum(1 for t in trays if t["status"] == STATUS_IN_PROGRESS)
    cnt_done     = sum(1 for t in trays if t["status"] == STATUS_COMPLETED)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            '<div class="status-card" style="background:#ffc107;">'
            '⏳ 待检测<br/>{}</div>'.format(cnt_pending),
            unsafe_allow_html=True)
    with c2:
        st.markdown(
            '<div class="status-card" style="background:#17a2b8;">'
            '🔄 检测中<br/>{}</div>'.format(cnt_progress),
            unsafe_allow_html=True)
    with c3:
        st.markdown(
            '<div class="status-card" style="background:#28a745;">'
            '✅ 已完成<br/>{}</div>'.format(cnt_done),
            unsafe_allow_html=True)

    st.divider()

    # ---- 扫码录入区 ----
    st.subheader("📷 扫码录入")
    st.caption("将光标置于下方输入框，扫码枪扫码后自动回车，系统自动带出料盘信息。")

    # 自动聚焦（JS 注入）
    st.markdown(
        """<script>
        setTimeout(function(){
            var el = window.parent.document
                         .querySelector('input[placeholder*="扫码"]');
            if(el) el.focus();
        }, 300);
        </script>""",
        unsafe_allow_html=True,
    )

    scan_input = st.text_input(
        "扫码 / 输入料盘号",
        placeholder="扫码或手动输入料盘号，如 LP-2026-001",
        key="scan_input",
    )

    if scan_input:
        tray = get_tray(scan_input.strip())
        if tray:
            st.success("✅ 已识别料盘号")
            col_a, col_b, col_c, col_d = st.columns(4)
            col_a.metric("料盘号", tray["tray_id"])
            col_b.metric("产品型号", tray["product_model"])
            col_c.metric("材料牌号", tray.get("material_grade", "—"))
            col_d.metric("工单号", tray.get("work_order", "—"))

            if st.button("✅ 确认 → 进入检测工作台", type="primary",
                         key="btn_confirm_scan"):
                tray["status"] = STATUS_IN_PROGRESS
                st.session_state.current_tray_id = tray["tray_id"]
                st.rerun()
        else:
            st.warning("⚠️ 未找到该料盘号，请检查或联系管理员。")

    # ---- 所有料盘列表 ----
    st.divider()
    st.subheader("📋 料盘清单")
    if trays:
        df = pd.DataFrame([{
            "料盘号": t["tray_id"],
            "产品型号": t["product_model"],
            "材料牌号": t.get("material_grade", ""),
            "工单号": t.get("work_order", ""),
            "状态": t["status"],
        } for t in trays])
        st.dataframe(df, use_container_width=True, hide_index=True)


# ============================================================
#  视图二：渗层检测工作台
# ============================================================
def view_workstation():
    st.header("② 渗层检测工作台")

    # 选择当前料盘
    tray_id = st.session_state.get("current_tray_id")
    trays = get_all_trays()

    if not tray_id:
        st.info("请先在「① 检测任务接收」中扫码或选择料盘号。")
        tray_options = [t["tray_id"] for t in trays]
        if tray_options:
            sel = st.selectbox("或手动选择料盘号", tray_options)
            if st.button("选定"):
                st.session_state.current_tray_id = sel
                st.rerun()
        return

    tray = get_tray(tray_id)
    if tray is None:
        st.error("料盘号不存在")
        return

    model = tray["product_model"]
    std = INSPECTION_STANDARDS.get(model, {})

    st.markdown("当前料盘：**{}** ｜ 产品型号：**{}** ｜ 材料：**{}**".format(
        tray["tray_id"], model, tray.get("material_grade", "")))
    st.divider()

    # 检查是否已有碳化物不合格 → 顶部红色预警条
    insp_existing = tray.get("inspection")
    if insp_existing and insp_existing.get("alert_level") == "critical":
        st.markdown(
            '<div class="alert-bar">🚨 红色预警：碳化物形态不合格！'
            '请立即隔离该批次并通知工艺工程师！</div>',
            unsafe_allow_html=True,
        )

    # ========== 区块一：硬度区 ==========
    st.subheader("🔩 区块一：硬度检测")
    hcol1, hcol2, hcol3 = st.columns(3)

    # --- CHD 三点 ---
    with hcol1:
        st.markdown("**有效硬化层深度 CHD (mm)**")
        chd_std = std.get("chd", {})
        chd_vals = []
        for i in range(3):
            v = st.number_input(
                "CHD 第{}点".format(i + 1),
                min_value=0.01, max_value=5.0,
                value=round(chd_std.get("target", 1.0), 2),
                step=0.01,
                key="chd_{}_{}".format(tray_id, i),
            )
            chd_vals.append(v)
        chd_mean = round(sum(chd_vals) / 3, 3)
        chd_range = round(max(chd_vals) - min(chd_vals), 3)
        st.metric("均值", "{} mm".format(chd_mean))
        st.metric("极差", "{} mm".format(chd_range))
        if chd_range > RANGE_ALERT_THRESHOLDS.get("chd", 0.15):
            st.warning("⚠️ 极差偏大，建议复检！")

    # --- 表面硬度 三点 ---
    with hcol2:
        st.markdown("**表面硬度 (HRC)**")
        sh_std = std.get("surface_hardness", {})
        sh_vals = []
        for i in range(3):
            v = st.number_input(
                "表面硬度 第{}点".format(i + 1),
                min_value=20.0, max_value=70.0,
                value=float(sh_std.get("target", 60)),
                step=0.5,
                key="sh_{}_{}".format(tray_id, i),
            )
            sh_vals.append(v)
        sh_mean = round(sum(sh_vals) / 3, 2)
        sh_range = round(max(sh_vals) - min(sh_vals), 2)
        st.metric("均值", "{} HRC".format(sh_mean))
        st.metric("极差", "{} HRC".format(sh_range))
        if sh_range > RANGE_ALERT_THRESHOLDS.get("surface_hardness", 3.0):
            st.warning("⚠️ 极差偏大，建议复检！")

    # --- 心部硬度 三点 ---
    with hcol3:
        st.markdown("**心部硬度 (HRC)**")
        ch_std = std.get("core_hardness", {})
        ch_vals = []
        for i in range(3):
            v = st.number_input(
                "心部硬度 第{}点".format(i + 1),
                min_value=20.0, max_value=55.0,
                value=float(ch_std.get("target", 38)),
                step=0.5,
                key="ch_{}_{}".format(tray_id, i),
            )
            ch_vals.append(v)
        ch_mean = round(sum(ch_vals) / 3, 2)
        ch_range = round(max(ch_vals) - min(ch_vals), 2)
        st.metric("均值", "{} HRC".format(ch_mean))
        st.metric("极差", "{} HRC".format(ch_range))
        if ch_range > RANGE_ALERT_THRESHOLDS.get("core_hardness", 3.0):
            st.warning("⚠️ 极差偏大，建议复检！")

    st.divider()

    # ========== 区块二：成分区 ==========
    st.subheader("🧪 区块二：成分检测")
    ccol1, ccol2 = st.columns(2)

    with ccol1:
        st.markdown("**表面碳含量 (%)**")
        sc_std = std.get("surface_carbon", {})
        sc_file = st.file_uploader(
            "上传光谱仪 CSV/ESG 文件（可选）",
            type=["csv", "esg", "txt"],
            key="sc_file_{}".format(tray_id),
        )
        sc_val = st.number_input(
            "表面碳含量 (%)",
            min_value=0.0, max_value=2.0,
            value=float(sc_std.get("target", 0.82)),
            step=0.01,
            key="sc_val_{}".format(tray_id),
        )
        if sc_file is not None:
            parsed = parse_composition_file(sc_file)
            if parsed is not None:
                st.success("📄 文件解析结果：{}%".format(parsed))
                sc_val = parsed

    with ccol2:
        st.markdown("**残余奥氏体含量 (%)**")
        ra_std = std.get("retained_austenite", {})
        ra_file = st.file_uploader(
            "上传残奥仪 CSV/ESG 文件（可选）",
            type=["csv", "esg", "txt"],
            key="ra_file_{}".format(tray_id),
        )
        ra_val = st.number_input(
            "残余奥氏体 (%)",
            min_value=0.0, max_value=60.0,
            value=float(ra_std.get("target", 5.0)),
            step=0.1,
            key="ra_val_{}".format(tray_id),
        )
        if ra_file is not None:
            parsed = parse_composition_file(ra_file)
            if parsed is not None:
                st.success("📄 文件解析结果：{}%".format(parsed))
                ra_val = parsed

    st.divider()

    # ========== 区块三：金相区 ==========
    st.subheader("🔬 区块三：金相检测")
    mcol1, mcol2 = st.columns([1, 2])

    with mcol1:
        mg_std = std.get("metallographic", {})
        max_grade = int(mg_std.get("usl", 3)) + 2
        mg_val = st.selectbox(
            "金相组织评级（级）",
            list(range(1, max_grade + 1)),
            index=min(int(mg_std.get("target", 2)) - 1, max_grade - 1),
            key="mg_val_{}".format(tray_id),
        )
        st.caption("标准范围：{}~{} 级".format(
            mg_std.get("lsl", 1), mg_std.get("usl", 3)))

    with mcol2:
        st.markdown("**金相照片上传（支持多张）**")
        mg_files = st.file_uploader(
            "选择金相照片",
            type=["png", "jpg", "jpeg", "bmp"],
            accept_multiple_files=True,
            key="mg_files_{}".format(tray_id),
        )
        if mg_files:
            cols = st.columns(min(len(mg_files), 4))
            for i, f in enumerate(mg_files):
                with cols[i % len(cols)]:
                    st.image(f, caption=f.name, width=150)
                    # （接上文 mcol2 内）
                    if st.button("保存 {}".format(f.name),
                                 key="save_mg_{}_{}".format(tray_id, i)):
                        add_image(tray_id, "metallographic", f.name,
                                  f.getvalue(), embed_in_report=True)
                        st.success("✅ 已保存：{}".format(f.name))

            # 显示已上传的金相图
            mg_imgs = get_images(tray_id, "metallographic")
            if mg_imgs:
                st.write("已上传 {} 张金相图：".format(len(mg_imgs)))
                cols2 = st.columns(min(len(mg_imgs), 4))
                for i, img in enumerate(mg_imgs):
                    with cols2[i % len(cols2)]:
                        st.image(img["data"], caption=img["file_name"], width=150)

    st.divider()

    # ========== 区块四：预警区（碳化物） ==========
    st.subheader("⚠️ 区块四：碳化物预警")

    # 判断当前是否已存在碳化物不合格
    _carbide_ng = False
    _existing_insp = tray.get("inspection")
    if _existing_insp and _existing_insp.get("carbide_result") == "不合格":
        _carbide_ng = True

    if _carbide_ng:
        st.markdown('<div class="carbide-alert">', unsafe_allow_html=True)

    wcol1, wcol2 = st.columns([1, 2])

    with wcol1:
        carbide_val = st.radio(
            "碳化物形态判定",
            ["合格", "不合格"],
            index=1 if _carbide_ng else 0,
            horizontal=True,
            key="carbide_{}".format(tray_id),
        )
        if carbide_val == "不合格":
            st.markdown(
                '<div class="alert-bar">🚨 红色预警：碳化物形态不合格！'
                '请立即隔离并通知工艺工程师！</div>',
                unsafe_allow_html=True,
            )

    with wcol2:
        st.markdown("**碳化物照片上传**")
        carb_files = st.file_uploader(
            "选择碳化物照片",
            type=["png", "jpg", "jpeg", "bmp"],
            accept_multiple_files=True,
            key="carb_files_{}".format(tray_id),
        )
        if carb_files:
            cols3 = st.columns(min(len(carb_files), 4))
            for i, f in enumerate(carb_files):
                with cols3[i % len(cols3)]:
                    st.image(f, caption=f.name, width=150)
                    if st.button("保存 {}".format(f.name),
                                 key="save_carb_{}_{}".format(tray_id, i)):
                        add_image(tray_id, "carbide", f.name,
                                  f.getvalue(), embed_in_report=True)
                        st.success("✅ 已保存：{}".format(f.name))

    if _carbide_ng:
        st.markdown('</div>', unsafe_allow_html=True)

    st.divider()

    # ========== 图片标签页查看 ==========
    st.subheader("🖼️ 检测图片总览")
    _render_image_tabs(tray_id)

    st.divider()

    # ========== 提交检测 ==========
    st.subheader("📤 提交检测")

    if st.button("✅ 提交全部检测数据", type="primary",
                 key="submit_inspection_{}".format(tray_id)):
        data = {
            "chd_values": chd_vals,
            "surface_hardness_values": sh_vals,
            "core_hardness_values": ch_vals,
            "surface_carbon": sc_val,
            "retained_austenite": ra_val,
            "metallographic_grade": mg_val,
            "carbide_result": carbide_val,
        }
        result = add_inspection_record(tray_id, data)

        if result.get("alert_level") == "critical":
            st.error("🚨 红色预警！存在严重不合格项（碳化物等），请立即处理！")
        elif result.get("alert_level") == "warning":
            st.warning("⚠️ 存在不合格项，请查看报告了解详情。")
        else:
            st.success("✅ 检测完成，该批次全部合格！")

        if result.get("nok_items"):
            st.markdown("**不合格项：**")
            for n in result["nok_items"]:
                st.markdown("- ❌ {} | 实测: {} | 标准: {}".format(
                    n["item"], n["measured"], n["standard"]))


def _render_image_tabs(tray_id):
    # type: (str) -> None
    """标签页分类查看/上传图片"""
    tab_names = list(IMAGE_CATEGORIES.values())
    tab_keys = list(IMAGE_CATEGORIES.keys())
    tabs = st.tabs(tab_names)

    for tab, cat_key in zip(tabs, tab_keys):
        with tab:
            cat_name = IMAGE_CATEGORIES[cat_key]

            # 上传
            up = st.file_uploader(
                "上传{}".format(cat_name),
                type=["png", "jpg", "jpeg", "bmp"],
                key="tab_up_{}_{}".format(tray_id, cat_key),
            )
            if up is not None:
                embed = st.checkbox(
                    "嵌入报告", value=True,
                    key="tab_embed_{}_{}".format(tray_id, cat_key),
                )
                if st.button("保存", key="tab_save_{}_{}".format(tray_id, cat_key)):
                    add_image(tray_id, cat_key, up.name, up.getvalue(), embed)
                    st.success("✅ 已保存")

            # 展示已有图片
            imgs = get_images(tray_id, cat_key)
            if imgs:
                st.write("已有 {} 张：".format(len(imgs)))
                cols = st.columns(min(len(imgs), 3))
                for i, img in enumerate(imgs):
                    with cols[i % len(cols)]:
                        st.image(img["data"], caption=img["file_name"], width=180)
                        badge = "📎嵌入" if img.get("embed_in_report") else "📁附件"
                        st.caption("{} | {}".format(badge, img.get("uploaded_at", "")))


# ============================================================
#  视图三：报告与判定结果
# ============================================================
def view_report():
    st.header("③ 报告与判定结果")

    trays = get_all_trays()
    tray_ids = [t["tray_id"] for t in trays]
    if not tray_ids:
        st.info("暂无检测数据。")
        return

    selected_tray_id = st.selectbox("选择料盘号", tray_ids, key="report_tray")
    tray = get_tray(selected_tray_id)
    if tray is None:
        return

    insp = tray.get("inspection")
    if insp is None:
        st.info("该料盘尚未完成检测。")
        return

    # ---- 顶部结论区 ----
    judgment = insp.get("judgment", "pending")
    nok_items = insp.get("nok_items", [])

    if judgment == "pass":
        st.markdown(
            '<div style="background:#d4edda;border:2px solid #28a745;'
            'border-radius:10px;padding:20px;text-align:center;">'
            '<span style="font-size:28px;font-weight:bold;color:#28a745;">'
            '✅ 该批次渗层检测合格，可放行，流转至磨削工序</span></div>',
            unsafe_allow_html=True,
        )
    else:
        names = "、".join(list(dict.fromkeys([n["item"] for n in nok_items])))
        st.markdown(
            '<div style="background:#f8d7da;border:2px solid #dc3545;'
            'border-radius:10px;padding:20px;text-align:center;">'
            '<span style="font-size:28px;font-weight:bold;color:#dc3545;">'
            '❌ 该批次因【{n}】不合格，建议报废/返工</span></div>'.format(n=names),
            unsafe_allow_html=True,
        )

    st.divider()

    # ---- 不合格清单 ----
    st.subheader("📋 不合格清单（全部料盘）")
    nok_df = generate_nok_list()
    if nok_df.empty:
        st.success("🎉 当前所有批次均无不合格项。")
    else:
        st.dataframe(nok_df, use_container_width=True, hide_index=True)

        # 导出 Excel
        excel_buf = io.BytesIO()
        with pd.ExcelWriter(excel_buf, engine="xlsxwriter") as writer:
            nok_df.to_excel(writer, index=False, sheet_name="不合格清单")
        st.download_button(
            "📥 导出不合格清单 (.xlsx)",
            data=excel_buf.getvalue(),
            file_name="不合格清单_{}.xlsx".format(
                datetime.now().strftime("%Y%m%d")),
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_nok_xlsx",
        )

    st.divider()

    # ---- 总报告生成 ----
    st.subheader("📄 总报告")

    if st.button("🔨 一键生成总报告", type="primary",
                 key="btn_gen_report"):
        html = generate_report(selected_tray_id)
        st.session_state["report_html_{}".format(selected_tray_id)] = html
        st.success("报告已生成！")

    rpt_key = "report_html_{}".format(selected_tray_id)
    if rpt_key in st.session_state:
        st.components.v1.html(st.session_state[rpt_key], height=600, scrolling=True)

        st.download_button(
            "📥 下载报告 (.html)",
            data=st.session_state[rpt_key],
            file_name="渗层检测报告_{}_{}.html".format(
                selected_tray_id, datetime.now().strftime("%Y%m%d")),
            mime="text/html",
            key="dl_report_html",
        )

    st.divider()

    # ---- 通知 QE ----
    st.subheader("📢 通知 QE")

    if st.button("🔔 生成通知", key="btn_notify"):
        msg = generate_notification(selected_tray_id)
        st.session_state["notification_{}".format(selected_tray_id)] = msg
        st.success("通知已生成！")

    ntf_key = "notification_{}".format(selected_tray_id)
    if ntf_key in st.session_state:
        st.text_area("通知内容（可直接复制发送至企业微信群）",
                     st.session_state[ntf_key], height=250,
                     key="ntf_view_{}".format(selected_tray_id))
        st.caption("💡 企业微信自动推送功能已预留接口，待 IT 支持后启用。")


# ============================================================
#  视图四：SPC 过程控制
# ============================================================
def view_spc():
    st.header("④ SPC 过程控制")

    trays = get_all_trays()
    completed = [t for t in trays if t.get("inspection") is not None]

    if not completed:
        st.info("暂无已完成的检测数据，无法生成 SPC 图。")
        return

    st.write("共 {} 个已完成批次参与 SPC 分析。".format(len(completed)))
    st.divider()

    render_spc_panel(trays)

    st.caption("💡 I-MR 控制图基于 ±3σ 原则。红色点为超出控制限的异常点。")


# ============================================================
#  页面路由
# ============================================================
if page == "① 检测任务接收":
    view_task_reception()
elif page == "② 渗层检测工作台":
    view_workstation()
elif page == "③ 报告与判定结果":
    view_report()
elif page == "④ SPC 过程控制":
    view_spc()


# ============================================================
#  部署与验证说明
# ============================================================
"""
==============================================================
  部署与验证指南
==============================================================

一、本地启动
────────────────────────────────────────────────────────────
1. 打开 CMD / PowerShell，执行：
   cd D:\\physical_lab_system

2. 安装依赖（首次运行）：
   pip install streamlit==1.37.1 pandas==2.2.3 plotly==5.24.1 Pillow==10.4.0 xlsxwriter==3.2.0

3. 启动应用：
   streamlit run app.py

4. 浏览器自动打开 http://localhost:8501

二、功能验证操作指南
────────────────────────────────────────────────────────────

【扫码录入】
  1. 进入「① 检测任务接收」
  2. 在输入框中输入 LP-2026-001（模拟扫码）
  3. 系统自动带出料盘号、产品型号、材料牌号、工单号
  4. 点击「确认 → 进入检测工作台」

【录入 6 大检测项目】
  1. 进入「② 渗层检测工作台」
  2. 硬度区：分别录入 CHD / 表面硬度 / 心部硬度各 3 个点
     → 系统自动计算均值和极差
     → 极差超阈值时提示"建议复检"
  3. 成分区：可手动输入或上传 CSV/ESG 文件
     → 上传后系统自动解析数值
  4. 金相区：下拉选择评级 + 上传照片（支持多张）
  5. 预警区：选择碳化物合格/不合格 + 上传照片
  6. 点击「提交全部检测数据」

【查看判定结果】
  1. 进入「③ 报告与判定结果」
  2. 选择料盘号，顶部显示绿色/红色结论
  3. 查看不合格清单，可导出 Excel
  4. 点击「一键生成总报告」→ 预览 → 下载

【触发碳化物红色预警】
  1. 在预警区选择「不合格」
  2. 提交后：
     - 整个预警区边框变红闪烁
     - 顶部弹出红色预警条
     - 报告中显示红色结论
  3. 在「③ 报告与判定结果」中点击「生成通知」查看通知内容

【SPC 过程控制】
  1. 进入「④ SPC 过程控制」
  2. 系统自动汇总所有已完成批次的 CHD、硬度等数据
  3. 生成 I 图和 MR 图，红色点为异常点

三、部署到 GitHub + Streamlit Cloud
────────────────────────────────────────────────────────────
1. 在 D:\\physical_lab_system 下初始化 Git：
   cd D:\\physical_lab_system
   git init
   git add .
   git commit -m "v3.0 渗层检测工作台"

2. 在 GitHub 上创建远程仓库（如 physical-lab-v3），然后：
   git remote add origin https://github.com/<你的用户名>/physical-lab-v3.git
   git branch -M main
   git push -u origin main

3. 确保仓库根目录包含 requirements.txt：
   streamlit==1.37.1
   pandas==2.2.3
   plotly==5.24.1
   Pillow==10.4.0
   xlsxwriter==3.2.0

4. 访问 https://share.streamlit.io
5. 用 GitHub 账号登录
6. 点击「New app」
7. 选择仓库 → 分支 main → 主文件 app.py
8. 点击「Deploy」
9. 等待 2~3 分钟部署完成，访问分配的 URL 即可

四、注意事项
────────────────────────────────────────────────────────────
- 所有数据存储在 session_state 中，刷新页面会重置为演示数据
- 生产环境建议替换为 SQLite / PostgreSQL
- 图片数据存在内存中，大量图片会占用服务器内存
- 企业微信推送已预留 _push_to_wecom() 接口，
  待 IT 提供 Webhook URL 后替换实现即可
==============================================================
"""         