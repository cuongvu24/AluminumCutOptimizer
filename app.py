import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from cutting_optimizer import optimize_cutting
from utils import validate_input_excel, create_output_excel
import io
import time

# Set page config
st.set_page_config(
    page_title="Phần Mềm Tối Ưu Cắt Nhôm",
    page_icon="✂️",
    layout="wide"
)

# Sidebar layout
with st.sidebar:
    st.title("✂️ Phần mềm tối ưu cắt nhôm")
    stock_length = st.number_input("Chiều Dài Tiêu Chuẩn (mm)", min_value=1000, value=6000, step=100)
    cutting_gap = st.number_input("Khoảng Cách Cắt (mm)", min_value=1, value=10, step=1)
    optimization_method = st.selectbox("Phương Pháp Tối Ưu", ["Tối Ưu Hiệu Suất Cao Nhất", "Tối Ưu Số Lượng Thanh"])
    optimization_options = st.radio("Tùy Chọn Tối Ưu Kích Thước Thanh", [
        "Sử Dụng Chiều Dài Cố Định",
        "Tối Ưu Trong Các Giá Trị Cố Định",
        "Tối Ưu Trong Khoảng Giá Trị"
    ])

    if optimization_options == "Tối Ưu Trong Khoảng Giá Trị":
        st.markdown("---")
        st.markdown("**Cấu Hình Khoảng Tối Ưu**")
        min_len = st.number_input("Chiều Dài Tối Thiểu (mm)", min_value=1000, max_value=10000, value=5500, step=100)
        max_len = st.number_input("Chiều Dài Tối Đa (mm)", min_value=min_len, max_value=20000, value=6500, step=100)
        step_len = st.number_input("Bước Tăng Kích Thước (mm)", min_value=100, value=100, step=100)

        stock_length_options = list(range(min_len, max_len + 1, step_len))
        optimize_stock_length = True
    elif optimization_options == "Tối Ưu Trong Các Giá Trị Cố Định":
        st.markdown("---")
        st.markdown("**Nhập Danh Sách Kích Thước Cố Định (mm)**")
        custom_lengths_text = st.text_area(
            "Nhập các kích thước, cách nhau bằng dấu phẩy hoặc xuống dòng:",
            value=" 5000, 5500, 6000, 6500"
        )

        if "," in custom_lengths_text:
            custom_lengths_raw = custom_lengths_text.split(",")
        else:
            custom_lengths_raw = custom_lengths_text.splitlines()

        stock_length_options = []
        for val in custom_lengths_raw:
            val = val.strip()
            if val.isdigit():
                stock_length_options.append(int(val))

        if not stock_length_options:
            st.warning("⚠️ Danh sách kích thước không hợp lệ. Sử dụng mặc định: 6000mm")
            stock_length_options = [6000]

        optimize_stock_length = True
        st.markdown(f"✅ Danh sách kích thước đã nhập: `{', '.join(map(str, stock_length_options))}`")
    else:
        stock_length_options = [stock_length]
        optimize_stock_length = False

st.title("✂️ Phần Mềm Tối Ưu Cắt Nhôm")
st.markdown("[📦 Xem mã nguồn trên GitHub](https://github.com/hero9xhn/AluminumCutOptimizer)")
st.markdown("""
Phần mềm này giúp tối ưu hóa các mẫu cắt nhôm để giảm thiểu lãng phí. Tải lên file Excel
với thông tin các thanh nhôm và kích thước, và nhận kế hoạch cắt tối ưu với số liệu chi tiết.
""")

# Hướng dẫn
with st.expander("📖 Hướng Dẫn Nhập Dữ Liệu", expanded=False):
    st.markdown("""
    File Excel của bạn nên chứa các cột sau:
    1. **Mã Thanh** - Mã/model của thanh nhôm
    2. **Chiều Dài** - Chiều dài yêu cầu của mỗi thanh (mm)
    3. **Số Lượng** - Số lượng cần thiết cho mỗi thanh

    Bạn có thể tải biểu mẫu mẫu ở cuối trang.
    """)

# Nội dung xử lý chính sẽ đặt ở giữa layout
uploaded_file = st.file_uploader("📤 Tải Lên File Excel Đầu Vào", type=["xlsx", "xls"])

if uploaded_file:
    try:
        input_data = pd.read_excel(uploaded_file)
        valid, message = validate_input_excel(input_data)

        if not valid:
            st.error(message)
        else:
            st.success("✅ Dữ liệu hợp lệ! Đang tối ưu hóa...")

            with st.spinner("🔄 Đang xử lý dữ liệu..."):
                start_time = time.time()
                result_df, patterns_df, summary_df = optimize_cutting(
                    input_data,
                    stock_length=stock_length,
                    cutting_gap=cutting_gap,
                    optimization_method=optimization_method,
                    stock_length_options=stock_length_options,
                    optimize_stock_length=optimize_stock_length
                )
                end_time = time.time()

            st.success(f"🎉 Tối ưu hóa hoàn tất sau {end_time - start_time:.2f} giây")
            st.subheader("📊 Bảng tổng hợp hiệu suất")

            # Tính toán hiệu suất nếu chưa có sẵn
            if 'Efficiency' not in summary_df.columns:
                try:
                    summary_df['Efficiency'] = summary_df['Total Length Needed (mm)'] / summary_df['Total Stock Length (mm)']
                    summary_df['Efficiency'] = summary_df['Efficiency'].fillna(0).apply(lambda x: f"{x*100:.2f}%")
                except Exception as eff_err:
                    st.warning(f"⚠️ Không thể tính hiệu suất: {eff_err}")
                
                summary_df = summary_df.rename(columns={
        'Profile Code': 'Mã Thanh',
        'Total Pieces': 'Tổng Số Đoạn',
        'Total Bars Used': 'Tổng Thanh Sử Dụng',
        'Total Length Needed (mm)': 'Tổng Chiều Dài Cần (mm)',
        'Total Stock Length (mm)': 'Tổng Chiều Dài Nguyên Liệu (mm)',
        'Waste (mm)': 'Phế Liệu (mm)',
        'Overall Efficiency': 'Hiệu Suất Tổng Thể',
        'Efficiency': 'Hiệu Suất (%)'
})
                st.dataframe(summary_df)
                st.subheader("📋 Danh sách mẫu cắt chi tiết")
                patterns_df = patterns_df.rename(columns={
        'Profile Code': 'Mã Thanh',
        'Bar Number': 'Số Thanh',
        'Stock Length': 'Chiều Dài Thanh',
        'Used Length': 'Chiều Dài Sử Dụng',
        'Remaining Length': 'Chiều Dài Còn Lại',
        'Efficiency': 'Hiệu Suất',
        'Cutting Pattern': 'Mẫu Cắt',
        'Pieces': 'Số Đoạn Cắt'
})
            st.dataframe(patterns_df)

            st.subheader("📥 Tải kết quả về máy")
            output = io.BytesIO()
            create_output_excel(output, result_df, patterns_df, summary_df, stock_length, cutting_gap)
            output.seek(0)
            st.download_button("📥 Tải xuống bảng Excel kết quả", output, "ket_qua_toi_uu.xlsx")

    except Exception as e:
        st.error(f"❌ Lỗi xử lý: {e}")

# Footer
st.markdown("---")
st.markdown("Phần Mềm Tối Ưu Cắt Nhôm © 2025 By Cuong Vu")
