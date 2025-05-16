import pandas as pd
import streamlit as st
import io
import time
from cutting_optimizer import optimize_cutting
from utils import create_output_excel, create_accessory_summary, validate_input_excel

st.set_page_config(page_title="Phần mềm Tối Ưu Nhôm & Phụ Kiện", layout="wide")
st.title("🔧 Ứng Dụng Tối Ưu Cắt Nhôm & Tổng Hợp Phụ Kiện")

uploaded_file = st.file_uploader("📤 Tải lên tệp Excel dữ liệu", type=["xlsx", "xls"])

tab_upload, tab1, tab2 = st.tabs(["📁 Tải Mẫu Nhập", "📦 Tổng Hợp Phụ Kiện", "✂️ Tối Ưu Cắt Nhôm"])

with tab_upload:
    st.subheader("📥 Tải xuống mẫu nhập liệu")
    st.markdown("""
    👉 Vui lòng sử dụng các mẫu bên dưới để đảm bảo định dạng chính xác khi nhập liệu:

    - **Mẫu Cắt Nhôm** gồm các cột: `Mã Thanh`, `Chiều Dài`, `Số Lượng`
    - **Mẫu Phụ Kiện** gồm các cột: `mã phụ kiện`, `tên phụ phiện`, `đơn vị tính`, `mã hàng`, `số lượng`
    """)

    # Mẫu cắt nhôm
    nhom_sample = pd.DataFrame({
        'Profile Code': ['ABC', 'ABC'],
        'Length': [1000, 1200],
        'Quantity': [3, 4]
    })
    out_nhom = io.BytesIO()
    nhom_sample.to_excel(out_nhom, index=False)
    out_nhom.seek(0)
    st.download_button("📄 Tải mẫu cắt nhôm", out_nhom, "mau_cat_nhom.xlsx")

    # Mẫu phụ kiện
    pk_sample = pd.DataFrame({
        'mã phụ kiện': ['PK001', 'PK002'],
        'tên phụ phiện': ['Gioăng', 'Bulong'],
        'đơn vị tính': ['cái', 'bộ'],
        'mã hàng': ['NHOM1', 'NHOM2'],
        'số lượng': [10, 20]
    })
    out_pk = io.BytesIO()
    pk_sample.to_excel(out_pk, index=False)
    out_pk.seek(0)
    st.download_button("📄 Tải mẫu phụ kiện", out_pk, "mau_phu_kien.xlsx")

with tab1:
    st.subheader("📦 Tổng Hợp Phụ Kiện")
    if uploaded_file:
        try:
            acc_df = pd.read_excel(uploaded_file)
            output = io.BytesIO()
            summary_df = create_accessory_summary(acc_df, output)
            output.seek(0)
            st.success("✅ Tổng hợp thành công!")
            st.dataframe(summary_df)
            st.download_button(
                "📥 Tải Xuống File Tổng Hợp Phụ Kiện",
                output,
                "tong_hop_phu_kien.xlsx"
            )
        except Exception as e:
            st.warning("⚠️ File không phù hợp hoặc thiếu cột cần thiết.")

with tab2:
    st.subheader("✂️ Tối Ưu Hóa Cắt Nhôm")
    if uploaded_file:
        try:
            df = pd.read_excel(uploaded_file)
            valid, message = validate_input_excel(df)
            if not valid:
                st.error(message)
            else:
                st.success("✅ Dữ liệu nhôm hợp lệ!")
                st.dataframe(df)

                stock_length = st.number_input("Chiều Dài Tiêu Chuẩn (mm)", 1000, 10000, 6000, 100)
                cutting_gap = st.number_input("Khoảng Cách Cắt (mm)", 1, 100, 10, 1)
                optimization_method = st.selectbox("Phương Pháp Tối Ưu", ["Tối Ưu Hiệu Suất Cao Nhất", "Tối Ưu Số Lượng Thanh"])
                length_text = st.text_input("Nhập các kích thước thanh (phân cách bằng dấu phẩy)", "5800, 6000, 6200, 6500")

                if st.button("🚀 Tối Ưu Hóa"):
                    try:
                        stock_length_options = [int(x.strip()) for x in length_text.split(",") if x.strip().isdigit()]
                        start_time = time.time()
                        result_df, patterns_df, summary_df = optimize_cutting(
                            df,
                            stock_length=stock_length,
                            cutting_gap=cutting_gap,
                            optimization_method=optimization_method,
                            stock_length_options=stock_length_options,
                            optimize_stock_length=True
                        )
                        elapsed = time.time() - start_time
                        st.success(f"✅ Hoàn tất trong {elapsed:.2f} giây")
                        st.dataframe(summary_df)

                        output = io.BytesIO()
                        create_output_excel(output, result_df, patterns_df, summary_df, stock_length, cutting_gap)
                        output.seek(0)
                        st.download_button(
                            "📥 Tải Xuống File Kết Quả Cắt Nhôm",
                            output,
                            "ket_qua_cat_nhom.xlsx"
                        )
                    except Exception as opt_err:
                        st.error(f"❌ Lỗi tối ưu hóa: {opt_err}")
        except Exception as e:
            st.error(f"❌ Lỗi xử lý file: {e}")


# Footer
st.markdown("---")
st.markdown("Phần Mềm Tối Ưu Cắt Nhôm © 2025 By Cường Vũ")
st.markdown("Mọi thắc mắc xin liên hệ Zalo 0977 487 639")
