import pandas as pd
import streamlit as st
import io
import time
import plotly.graph_objects as go
from cutting_optimizer import optimize_cutting
from utils import (
    create_output_excel, 
    create_accessory_summary, 
    validate_input_excel, 
    save_optimization_history, 
    load_optimization_history, 
    delete_optimization_history_entry
)
import uuid
from datetime import datetime
import threading
import json

# -------------------------------
# Hàm hiển thị mô phỏng cắt thanh
# -------------------------------
def display_pattern(row, cutting_gap):
    pattern = row['Mẫu Cắt']
    parts = pattern.split('+')
    current_pos = 0
    fig = go.Figure()

    for i, part in enumerate(parts):
        length = float(part)
        color = f"rgba({(i*40)%255}, {(i*70)%255}, {(i*90)%255}, 0.7)" if i > 0 else "rgba(255, 100, 100, 0.9)"
        fig.add_shape(
            type="rect",
            x0=current_pos, x1=current_pos + length,
            y0=0, y1=1,
            line=dict(width=1),
            fillcolor=color
        )
        fig.add_annotation(
            x=current_pos + length / 2, y=0.5,
            text=str(int(length)) if length % 1 == 0 else f"{length:.1f}",
            showarrow=False,
            font=dict(size=10, color="white")
        )
        current_pos += length + cutting_gap

    fig.update_layout(
        height=100,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(title="", range=[0, row['Chiều Dài Thanh']]),
        yaxis=dict(visible=False),
        showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True, key=f"plot_{row['Số Thanh']}_{uuid.uuid4()}")

# -------------------------------
# App config
# -------------------------------
st.set_page_config(page_title="Phần mềm Hỗ Trợ Sản Xuất Cửa", layout="wide")
st.title("🤖 Phần mềm Hỗ Trợ Sản Xuất Cửa")

# Tải file
uploaded_file = st.file_uploader("📤 Tải lên tệp Excel dữ liệu", type=["xlsx", "xls"])
if 'result_data' not in st.session_state:
    st.session_state.result_data = None

# Tabs chính
tab_intro, tab_upload, tab_accessory, tab_cutting = st.tabs(
    ["📖 Giới Thiệu", "📁 Tải Mẫu Nhập", "📦 Tổng Hợp Phụ Kiện", "✂️ Tối Ưu Cắt Nhôm"]
)

# -------------------------------
# Tab Giới Thiệu
# -------------------------------
with tab_intro:
    st.header("📖 Giới thiệu và Hướng dẫn")
    st.markdown("""
    - **Chức năng**: Hỗ trợ tối ưu hóa cắt nhôm, quản lý phụ kiện, giảm phế liệu.
    - Tải đúng mẫu, nhập liệu chính xác.
    - Chọn kích thước, khoảng cách cắt, phương pháp tối ưu, bấm **Tối Ưu Hóa**.
    - Xem mô phỏng cắt chi tiết.
    """)

# -------------------------------
# Tab Tải Mẫu Nhập
# -------------------------------
with tab_upload:
    st.header("📥 Tải xuống file mẫu")
    nhom_sample = pd.DataFrame({
        'Mã Thanh': ['ABC'], 'Chiều Dài': [1000], 'Số Lượng': [2], 'Mã Cửa': ['D001']
    })
    out_nhom = io.BytesIO()
    nhom_sample.to_excel(out_nhom, index=False)
    out_nhom.seek(0)
    st.download_button("📄 Tải Mẫu Cắt Nhôm", out_nhom, "mau_cat_nhom.xlsx")

    pk_sample = pd.DataFrame({
        'Mã phụ kiện': ['PK001'], 'Tên phụ phiện': ['Gioăng'],
        'Đơn vị tính': ['cái'], 'Số lượng': [10]
    })
    out_pk = io.BytesIO()
    pk_sample.to_excel(out_pk, index=False)
    out_pk.seek(0)
    st.download_button("📄 Tải Mẫu Phụ Kiện", out_pk, "mau_phu_kien.xlsx")

# -------------------------------
# Tab Tổng Hợp Phụ Kiện
# -------------------------------
with tab_accessory:
    st.header("📦 Tổng Hợp Phụ Kiện")
    if uploaded_file:
        try:
            acc_df = pd.read_excel(uploaded_file)
            output = io.BytesIO()
            summary_df = create_accessory_summary(acc_df, output)
            output.seek(0)
            st.success("✅ Đã tổng hợp phụ kiện.")
            st.dataframe(summary_df)
            st.download_button("📥 Tải Xuống Kết Quả", output, "tong_hop_phu_kien.xlsx")
        except:
            st.warning("⚠️ File không phù hợp!")

# -------------------------------
# Tab Tối Ưu Cắt Nhôm
# -------------------------------
with tab_cutting:
    st.header("✂️ Tối Ưu Cắt Nhôm")
    if uploaded_file:
        try:
            df = pd.read_excel(uploaded_file)
            valid, msg = validate_input_excel(df)
            if not valid:
                st.error(msg)
            else:
                st.success("✅ File hợp lệ.")
                st.dataframe(df)
                col1, col2 = st.columns(2)
                with col1:
                    length_opts = st.text_input("Kích Thước Thanh (phẩy)", "5800, 6000")
                with col2:
                    gap = st.number_input("Khoảng Cách Cắt", 1, 100, 10, 1)

                if st.button("🚀 Tối Ưu Hóa"):
                    try:
                        stock_lengths = [int(x.strip()) for x in length_opts.split(',') if x.strip().isdigit()]
                        result_df, patterns_df, summary_df = optimize_cutting(
                            df, stock_length=stock_lengths[0],
                            cutting_gap=gap,
                            stock_length_options=stock_lengths,
                            optimize_stock_length=True
                        )
                        st.session_state.result_data = (result_df, patterns_df, summary_df, stock_lengths, gap)
                    except Exception as e:
                        st.error(f"Lỗi tối ưu: {e}")

    if st.session_state.result_data:
        result_df, patterns_df, summary_df, stock_lengths, gap = st.session_state.result_data
        st.subheader("📊 Bảng Tổng Hợp Hiệu Suất")
        st.dataframe(summary_df)
        st.subheader("📋 Danh Sách Mẫu Cắt")
        st.dataframe(patterns_df)
        st.subheader("📄 Chi Tiết Mảnh")
        st.dataframe(result_df)

        st.subheader("📏 Mô Phỏng")
        selected = st.selectbox("Chọn Mã Thanh", patterns_df['Mã Thanh'].unique())
        filtered = patterns_df[patterns_df['Mã Thanh'] == selected]
        for _, row in filtered.iterrows():
            st.markdown(f"**🔹 #{row['Số Thanh']} | {selected} | {row['Chiều Dài Thanh']}mm**")
            display_pattern(row, gap)

        output = io.BytesIO()
        create_output_excel(output, result_df, patterns_df, summary_df, stock_lengths, gap)
        output.seek(0)
        st.download_button("📥 Tải Xuống File Kết Quả", output, "ket_qua_cat_nhom.xlsx")

# -------------------------------
st.markdown("---")
st.info("💡 Liên hệ hỗ trợ Zalo: 0977 487 639")
