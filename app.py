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
)
import uuid

# ============== Hàm mô phỏng cắt thanh ==============
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
    unique_key = f"plot_{row['Số Thanh']}_{uuid.uuid4()}"
    st.plotly_chart(fig, use_container_width=True, key=unique_key)

# ============== Cài đặt trang ==============
st.set_page_config(page_title="Phần mềm Hỗ Trợ Sản Xuất Cửa", layout="wide")
st.title("🤖 Phần mềm Hỗ Trợ Sản Xuất Cửa")

uploaded_file = st.file_uploader("📤 Tải tệp Excel", type=["xlsx", "xls"])

if 'result_data' not in st.session_state:
    st.session_state.result_data = None

tab_intro, tab_upload, tab_pk, tab_cut = st.tabs(
    ["📖 Giới Thiệu", "📁 Tải Mẫu", "📦 Phụ Kiện", "✂️ Tối Ưu Cắt"]
)

# ============== Tab Giới Thiệu ==============
with tab_intro:
    st.subheader("📖 Giới Thiệu")
    st.info("""
    👉 Ứng dụng tối ưu hóa cắt nhôm & tổng hợp phụ kiện cho sản xuất cửa.  
    👉 Chọn tab **Tải Mẫu** để tải file chuẩn.  
    👉 Chạy tối ưu hóa & xuất báo cáo dễ dàng!
    """)

# ============== Tab Tải Mẫu ==============
with tab_upload:
    st.header("📁 Tải Mẫu Nhập")
    nhom_sample = pd.DataFrame({
        'Mã Thanh': ['TNG1'],
        'Chiều Dài': [2000],
        'Số Lượng': [2],
        'Mã Cửa': ['D001']
    })
    out1 = io.BytesIO()
    nhom_sample.to_excel(out1, index=False)
    out1.seek(0)
    st.download_button("📄 Mẫu Cắt Nhôm", out1, "mau_cat_nhom.xlsx")

    pk_sample = pd.DataFrame({
        'Mã phụ kiện': ['PK001'],
        'Tên phụ phiện': ['Gioăng'],
        'Đơn vị tính': ['cái'],
        'Số lượng': [10]
    })
    out2 = io.BytesIO()
    pk_sample.to_excel(out2, index=False)
    out2.seek(0)
    st.download_button("📄 Mẫu Phụ Kiện", out2, "mau_phu_kien.xlsx")

# ============== Tab Tổng Hợp Phụ Kiện ==============
with tab_pk:
    st.header("📦 Tổng Hợp Phụ Kiện")
    if uploaded_file:
        try:
            df = pd.read_excel(uploaded_file)
            output = io.BytesIO()
            summary = create_accessory_summary(df, output)
            output.seek(0)
            st.success("✅ Tổng hợp thành công!")
            st.dataframe(summary, use_container_width=True)
            st.download_button("📥 Tải File Phụ Kiện", output, "tong_hop_phu_kien.xlsx")
        except Exception as e:
            st.warning(f"⚠️ Lỗi: {e}")

# ============== Tab Tối Ưu Cắt Nhôm ==============
with tab_cut:
    st.header("✂️ Tối Ưu Cắt Nhôm")
    if uploaded_file:
        try:
            df = pd.read_excel(uploaded_file)
            valid, msg = validate_input_excel(df)
            if not valid:
                st.error(msg)
            else:
                st.success("✅ File hợp lệ.")
                st.dataframe(df, use_container_width=True)
                col1, col2, col3 = st.columns(3)
                with col1:
                    lengths_text = st.text_input("Kích Thước Thanh (mm, phẩy)", "5800, 6000")
                with col2:
                    gap = st.number_input("Khoảng Cách Cắt (mm)", 1, 100, 10, 1)
                with col3:
                    method = st.selectbox("Phương Pháp Tối Ưu", ["Tối Ưu Hiệu Suất Cao Nhất", "Tối Ưu Số Lượng Thanh"])

                if st.button("🚀 Tối Ưu Hóa"):
                    stock_lengths = [int(x.strip()) for x in lengths_text.split(',') if x.strip().isdigit()]
                    if not stock_lengths:
                        st.error("Nhập ít nhất 1 kích thước.")
                    else:
                        try:
                            start = time.time()
                            result_df, patterns_df, summary_df = optimize_cutting(
                                df,
                                stock_length=stock_lengths[0],
                                cutting_gap=gap,
                                stock_length_options=stock_lengths,
                                optimize_stock_length=True
                            )

                            # Thêm Mã Cửa từ file nguồn
                            if 'Mã Cửa' in df.columns:
                                id_to_cua = {}
                                for _, row in df.iterrows():
                                    for i in range(int(row['Số Lượng'])):
                                        id_to_cua[f"{row['Mã Thanh']}_{i+1}"] = row['Mã Cửa']

                                result_df['Mã Cửa'] = result_df['Item ID'].map(id_to_cua)

                            # Đồng nhất cột
                            result_df = result_df.rename(columns={'Profile Code': 'Mã Thanh', 'Item ID': 'Mã Mảnh', 'Bar Number': 'Số Thanh'})
                            patterns_df = patterns_df.rename(columns={
                                'Profile Code': 'Mã Thanh',
                                'Bar Number': 'Số Thanh',
                                'Stock Length': 'Chiều Dài Thanh',
                                'Used Length': 'Chiều Dài Sử Dụng',
                                'Remaining Length': 'Chiều Dài Còn Lại',
                                'Efficiency': 'Hiệu Suất',
                                'Cutting Pattern': 'Mẫu Cắt',
                                'Pieces': 'Số Mảnh'
                            })
                            summary_df = summary_df.rename(columns={
                                'Profile Code': 'Mã Thanh',
                                'Total Pieces': 'Tổng Số Đoạn',
                                'Total Bars Used': 'Tổng Thanh Sử Dụng',
                                'Total Length Needed (mm)': 'Tổng Chiều Dài Cần (mm)',
                                'Total Stock Length (mm)': 'Tổng Chiều Dài Nguyên Liệu (mm)',
                                'Waste (mm)': 'Phế Liệu (mm)',
                                'Overall Efficiency': 'Hiệu Suất Tổng Thể'
                            })

                            st.session_state.result_data = (result_df, patterns_df, summary_df, stock_lengths, gap)
                            elapsed = time.time() - start
                            st.success(f"✅ Hoàn tất sau {elapsed:.1f}s")
                        except Exception as e:
                            st.error(f"Lỗi: {e}")
        except Exception as e:
            st.error(f"Lỗi: {e}")
    else:
        st.info("📤 Vui lòng tải file!")

    if st.session_state.result_data:
        result_df, patterns_df, summary_df, stock_lengths, gap = st.session_state.result_data

        st.subheader("📊 Bảng Hiệu Suất")
        st.dataframe(summary_df, use_container_width=True)

        st.subheader("📋 Mẫu Cắt")
        st.dataframe(patterns_df, use_container_width=True)

        st.subheader("📄 Chi Tiết Mảnh (Có Mã Cửa)")
        st.dataframe(result_df, use_container_width=True)

        st.subheader("📊 Mô Phỏng")
        selected_profile = st.selectbox("Chọn Mã Thanh", patterns_df['Mã Thanh'].unique())
        filtered = patterns_df[patterns_df['Mã Thanh'] == selected_profile]
        for _, row in filtered.iterrows():
            st.markdown(f"🔹 #{row['Số Thanh']} | {selected_profile} | {row['Chiều Dài Thanh']}mm")
            display_pattern(row, gap)

        out = io.BytesIO()
        create_output_excel(out, result_df, patterns_df, summary_df, stock_lengths, gap)
        out.seek(0)
        st.download_button("📥 Tải File Kết Quả", out, "ket_qua_cat_nhom.xlsx")

st.markdown("---")
st.markdown("Liên hệ Zalo: 0977 487 639 © 2025")
