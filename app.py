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

# ================== Hàm mô phỏng ==================
def display_pattern(row, cutting_gap):
    pattern = row['Mẫu Cắt']
    parts = pattern.split('+')
    current_pos = 0
    fig = go.Figure()

    for i, part in enumerate(parts):
        length = float(part)
        color = f"rgba({(i*50)%255}, {(i*80)%255}, {(i*110)%255}, 0.8)" if i > 0 else "rgba(255, 80, 80, 0.9)"
        fig.add_shape(
            type="rect",
            x0=current_pos, x1=current_pos + length,
            y0=0, y1=1,
            line=dict(width=1),
            fillcolor=color
        )
        fig.add_annotation(
            x=current_pos + length / 2, y=0.5,
            text=f"{length:.1f}" if length % 1 else str(int(length)),
            showarrow=False,
            font=dict(size=10, color="white")
        )
        current_pos += length + cutting_gap

    fig.update_layout(
        height=100,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(title="", range=[0, row['Chiều Dài Thanh']]),
        yaxis=dict(visible=False)
    )
    st.plotly_chart(fig, use_container_width=True, key=f"plot_{row['Số Thanh']}_{uuid.uuid4()}")

# ================== Trang ==================
st.set_page_config(page_title="Phần mềm Hỗ Trợ Sản Xuất Cửa", layout="wide")
st.title("🧩 Phần mềm Hỗ Trợ Sản Xuất Cửa")

uploaded_file = st.file_uploader("📤 Tải tệp Excel", type=["xlsx", "xls"])

if 'result_data' not in st.session_state:
    st.session_state.result_data = None

tab_intro, tab_upload, tab_pk, tab_cut = st.tabs(["📖 Giới Thiệu", "📁 Tải Mẫu", "📦 Phụ Kiện", "✂️ Tối Ưu Cắt"])

# ================== Giới Thiệu ==================
with tab_intro:
    st.subheader("📖 Giới Thiệu và Hướng Dẫn")
    st.markdown("""
    **✅ Phần mềm hỗ trợ cắt nhôm & phụ kiện:**  
    - Hỗ trợ nhập file Excel.  
    - Giảm phế liệu, xuất file báo cáo.  
    - Quản lý **Mã Cửa**, **Mã Mảnh** đầy đủ.

    **Bước 1:** Tải mẫu.  
    **Bước 2:** Nhập dữ liệu.  
    **Bước 3:** Tải lên file.  
    **Bước 4:** Chạy tối ưu & tải file kết quả!
    """)

# ================== Mẫu ==================
with tab_upload:
    st.header("📁 Tải Mẫu")
    nhom = pd.DataFrame({
        'Mã Thanh': ['ABC1'],
        'Chiều Dài': [1000],
        'Số Lượng': [2],
        'Mã Cửa': ['D1']
    })
    pk = pd.DataFrame({
        'Mã phụ kiện': ['PK01'],
        'Tên phụ phiện': ['Bulong'],
        'Đơn vị tính': ['cái'],
        'Số lượng': [10]
    })

    out1, out2 = io.BytesIO(), io.BytesIO()
    nhom.to_excel(out1, index=False)
    pk.to_excel(out2, index=False)
    out1.seek(0)
    out2.seek(0)

    st.download_button("📄 Mẫu Cắt Nhôm", out1, "mau_cat_nhom.xlsx")
    st.download_button("📄 Mẫu Phụ Kiện", out2, "mau_phu_kien.xlsx")

# ================== Phụ Kiện ==================
with tab_pk:
    st.header("📦 Tổng Hợp Phụ Kiện")
    if uploaded_file:
        try:
            df = pd.read_excel(uploaded_file)
            out = io.BytesIO()
            summary = create_accessory_summary(df, out)
            out.seek(0)
            st.dataframe(summary)
            st.download_button("📥 Tải File Phụ Kiện", out, "tong_hop_phu_kien.xlsx")
        except:
            st.warning("⚠️ File phụ kiện không hợp lệ!")

# ================== Tối Ưu Cắt ==================
with tab_cut:
    st.header("✂️ Tối Ưu Cắt Nhôm")
    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        valid, msg = validate_input_excel(df)
        if not valid:
            st.error(msg)
        else:
            st.dataframe(df)
            col1, col2, col3 = st.columns(3)
            lengths = col1.text_input("Kích Thước Thanh (phẩy)", "5800, 6000")
            gap = col2.number_input("Khoảng Cách Cắt (mm)", 1, 100, 10)
            method = col3.selectbox("Phương Pháp", ["Tối Ưu Hiệu Suất Cao Nhất", "Tối Ưu Số Lượng Thanh"])

            if st.button("🚀 Tối Ưu"):
                stocks = [int(x.strip()) for x in lengths.split(',') if x.strip().isdigit()]
                if not stocks:
                    st.error("Thiếu kích thước thanh.")
                else:
                    res, pat, sum_df = optimize_cutting(
                        df,
                        stock_length=stocks[0],
                        cutting_gap=gap,
                        optimization_method=method,
                        stock_length_options=stocks,
                        optimize_stock_length=True
                    )
                    # Thêm Mã Cửa vào result
                    if 'Mã Cửa' in df.columns:
                        id_map = {}
                        for _, row in df.iterrows():
                            for i in range(int(row['Số Lượng'])):
                                id_map[f"{row['Mã Thanh']}_{i+1}"] = row['Mã Cửa']
                        res['Mã Cửa'] = res['Item ID'].map(id_map)

                    res = res.rename(columns={
                        'Profile Code': 'Mã Thanh',
                        'Item ID': 'Mã Mảnh',
                        'Length': 'Chiều Dài',
                        'Bar Number': 'Số Thanh'
                    })

                    st.session_state.result_data = (res, pat, sum_df, stocks, gap)
                    st.success("✅ Tối ưu xong!")

    if st.session_state.result_data:
        res, pat, sum_df, stocks, gap = st.session_state.result_data
        st.subheader("📊 Hiệu Suất")
        st.dataframe(sum_df)
        st.subheader("📋 Mẫu Cắt")
        st.dataframe(pat)
        st.subheader("📄 Chi Tiết Mảnh (Có Mã Cửa)")
        st.dataframe(res)

        st.subheader("📊 Mô Phỏng")
        sel = st.selectbox("Chọn Mã Thanh", pat['Mã Thanh'].unique())
        for idx, row in pat[pat['Mã Thanh'] == sel].iterrows():
            st.markdown(f"🔹 #{row['Số Thanh']} | {sel} | {row['Chiều Dài Thanh']}mm")
            display_pattern(row, gap)

        out = io.BytesIO()
        create_output_excel(out, res, pat, sum_df, stocks, gap)
        out.seek(0)
        st.download_button("📥 Tải Kết Quả", out, "ket_qua_cat_nhom.xlsx")

# ================== Footer ==================
st.markdown("---")
st.markdown("📞 Zalo **0977 487 639** — Ứng dụng hỗ trợ sản xuất cửa © 2025")
