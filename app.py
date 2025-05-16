import pandas as pd
import streamlit as st
import io

def validate_input_excel(df):
    required_columns = ["Profile Code", "Length", "Quantity"]
    vietnamese_columns = {
        "Mã Thanh": "Profile Code",
        "Chiều Dài": "Length",
        "Số Lượng": "Quantity"
    }

    for vn_col, en_col in vietnamese_columns.items():
        if vn_col in df.columns:
            df.rename(columns={vn_col: en_col}, inplace=True)

    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        return False, f"Thiếu các cột bắt buộc: {', '.join(missing)}"

    try:
        df['Length'] = pd.to_numeric(df['Length'])
        df['Quantity'] = pd.to_numeric(df['Quantity'])
    except ValueError:
        return False, "Chiều Dài và Số Lượng phải là số"

    if (df['Length'] <= 0).any():
        return False, "Chiều Dài phải > 0"
    if (df['Quantity'] <= 0).any():
        return False, "Số Lượng phải > 0"
    if df['Profile Code'].isnull().any() or (df['Profile Code'] == '').any():
        return False, "Mã Thanh không được để trống"
    if len(df) == 0:
        return False, "Tệp không có dữ liệu"

    return True, "Tệp hợp lệ"


def create_accessory_summary(input_df, output_stream):
    required_cols = ['mã phụ kiện', 'tên phụ phiện', 'đơn vị tính', 'mã hàng', 'số lượng']
    missing = [col for col in required_cols if col not in input_df.columns]
    if missing:
        raise ValueError(f"Thiếu cột: {', '.join(missing)}")

    grouped = input_df.groupby(['mã phụ kiện', 'tên phụ phiện', 'đơn vị tính', 'mã hàng'])['số lượng'].sum().reset_index()
    grouped = grouped.rename(columns={'số lượng': 'Tổng Số Lượng'})

    with pd.ExcelWriter(output_stream, engine='openpyxl') as writer:
        grouped.to_excel(writer, sheet_name="Tổng Hợp Phụ Kiện", index=False)

    return grouped

# Giao diện dùng chung cho cả phụ kiện và nhôm
st.header("📤 Tải Lên Tệp Dữ Liệu Excel")
uploaded_file = st.file_uploader("Chọn Tệp Excel (Phụ Kiện hoặc Nhôm)", type=["xlsx", "xls"])

# Tabs riêng biệt cho hai loại xử lý
tab_upload, tab1, tab2 = st.tabs(["📁 Tải Mẫu Nhập", "📦 Tổng Hợp Phụ Kiện", "✂️ Tối Ưu Hóa Cắt Nhôm"])

with tab_upload:
    st.subheader("📥 Tải xuống mẫu nhập liệu")
    import io
    sample_df = pd.DataFrame({
        'Profile Code': ['ABC', 'ABC'],
        'Length': [1000, 1200],
        'Quantity': [3, 4]
    })
    output = io.BytesIO()
    sample_df.to_excel(output, index=False)
    output.seek(0)
    st.download_button("📄 Tải mẫu cắt nhôm", output, "mau_cat_nhom.xlsx")

    sample2 = pd.DataFrame({
        'mã phụ kiện': ['PK001', 'PK002'],
        'tên phụ phiện': ['Gioăng', 'Bulong'],
        'đơn vị tính': ['cái', 'bộ'],
        'mã hàng': ['NHOM1', 'NHOM2'],
        'số lượng': [10, 20]
    })
    out2 = io.BytesIO()
    sample2.to_excel(out2, index=False)
    out2.seek(0)
    st.download_button("📄 Tải mẫu phụ kiện", out2, "mau_phu_kien.xlsx")

with tab_upload:
    st.subheader("📥 Tải xuống mẫu nhập liệu")
    st.markdown("""
    👉 Vui lòng sử dụng các mẫu bên dưới để đảm bảo định dạng chính xác khi nhập liệu:

    - **Mẫu Cắt Nhôm** gồm các cột: `Mã Thanh`, `Chiều Dài`, `Số Lượng`
    - **Mẫu Phụ Kiện** gồm các cột: `mã phụ kiện`, `tên phụ phiện`, `đơn vị tính`, `mã hàng`, `số lượng`

    Sau khi điền dữ liệu, hãy quay lại tab tương ứng và tải lên file để tính toán.
    """)
    import io
    sample_df = pd.DataFrame({
        'Profile Code': ['ABC', 'ABC'],
        'Length': [1000, 1200],
        'Quantity': [3, 4]
    })
    output = io.BytesIO()
    sample_df.to_excel(output, index=False)
    output.seek(0)
    st.download_button("📄 Tải mẫu cắt nhôm", output, "mau_cat_nhom.xlsx")

    sample2 = pd.DataFrame({
        'mã phụ kiện': ['PK001', 'PK002'],
        'tên phụ phiện': ['Gioăng', 'Bulong'],
        'đơn vị tính': ['cái', 'bộ'],
        'mã hàng': ['NHOM1', 'NHOM2'],
        'số lượng': [10, 20]
    })
    out2 = io.BytesIO()
    sample2.to_excel(out2, index=False)
    out2.seek(0)
    st.download_button("📄 Tải mẫu phụ kiện", out2, "mau_phu_kien.xlsx")

# Tabs vẫn hiện ra ngay cả khi chưa upload file
if True:
    tab1, tab2 = st.tabs(["📦 Tổng Hợp Phụ Kiện", "✂️ Tối Ưu Hóa Cắt Nhôm"])

    with tab1:
        try:
            acc_df = pd.read_excel(uploaded_file)
            st.success("✅ File hợp lệ, đang tổng hợp phụ kiện...")
            output = io.BytesIO()
            summary_df = create_accessory_summary(acc_df, output)
            output.seek(0)
            st.subheader("📋 Kết Quả Tổng Hợp Phụ Kiện")
            st.dataframe(summary_df)
            st.download_button(
                label="📥 Tải Xuống Kết Quả Phụ Kiện",
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
                import time
from cutting_optimizer import optimize_cutting
from utils import create_output_excel

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
