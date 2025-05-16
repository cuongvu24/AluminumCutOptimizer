import streamlit as st
import pandas as pd
import io
import time
from utils import create_accessory_summary, validate_input_excel
from cutting_optimizer import optimize_cutting
from utils import create_output_excel

# Giao diện dùng chung
st.header("📤 Tải Lên File Dữ Liệu")
uploaded_file = st.file_uploader("Chọn File Excel (phụ kiện hoặc thanh nhôm)", type=["xlsx", "xls"])

# Tabs riêng biệt
if uploaded_file:
    tab1, tab2 = st.tabs(["📦 Tính Phụ Kiện", "✂️ Tối Ưu Cắt Nhôm"])

    with tab1:
        try:
            acc_df = pd.read_excel(uploaded_file)
            st.success("✅ File hợp lệ, đang tổng hợp phụ kiện...")
            output = io.BytesIO()
            summary_df = create_accessory_summary(acc_df, output)
            output.seek(0)
            st.subheader("📋 Bảng Tổng Hợp Phụ Kiện")
            st.dataframe(summary_df)
            st.download_button(
                label="📥 Tải Xuống File Tổng Hợp Phụ Kiện",
                data=output,
                file_name="tong_hop_phu_kien.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except Exception as e:
            st.warning("Không phải file phụ kiện hoặc thiếu cột phù hợp.")

    with tab2:
        try:
            df = pd.read_excel(uploaded_file)
            valid, message = validate_input_excel(df)
            if not valid:
                st.error(message)
            else:
                st.success("✅ Dữ liệu nhôm hợp lệ! Sẵn sàng xử lý tối ưu hóa.")
                st.dataframe(df)

                stock_length = st.number_input("Chiều Dài Tiêu Chuẩn (mm)", min_value=1000, value=6000, step=100)
                cutting_gap = st.number_input("Khoảng Cách Cắt (mm)", min_value=1, value=10, step=1)
                optimization_method = st.selectbox("Phương Pháp Tối Ưu", ["Tối Ưu Hiệu Suất Cao Nhất", "Tối Ưu Số Lượng Thanh"])
                length_options_text = st.text_input("Nhập các kích thước thanh có thể dùng (cách nhau bởi dấu phẩy)", "5800, 6000, 6200, 6500")

                if st.button("🚀 Bắt đầu tối ưu hóa"):
                    with st.spinner("🔄 Đang tối ưu hóa..."):
                        try:
                            stock_length_options = [int(x.strip()) for x in length_options_text.split(",") if x.strip().isdigit()]
                            start_time = time.time()
                            result_df, patterns_df, summary_df = optimize_cutting(
                                df,
                                stock_length=stock_length,
                                cutting_gap=cutting_gap,
                                optimization_method=optimization_method,
                                stock_length_options=stock_length_options,
                                optimize_stock_length=True
                            )
                            end_time = time.time()
                            st.success(f"✅ Tối ưu hoàn tất sau {end_time - start_time:.2f} giây")
                            st.dataframe(summary_df)
                            output = io.BytesIO()
                            create_output_excel(output, result_df, patterns_df, summary_df, stock_length, cutting_gap)
                            output.seek(0)
                            st.download_button(
                                label="📥 Tải Xuống Kết Quả Cắt Nhôm",
                                data=output,
                                file_name="ket_qua_cat_nhom.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                        except Exception as opt_e:
                            st.error(f"❌ Lỗi tối ưu hóa: {opt_e}")
        except Exception as e:
            st.error(f"❌ Lỗi xử lý: {e}")
# Footer
st.markdown("---")
st.markdown("Phần Mềm Tối Ưu Cắt Nhôm © 2025 By Cường Vũ")
st.markdown("Mọi thắc mắc xin liên hệ Zalo 0977 487 639")
