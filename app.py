import pandas as pd
import streamlit as st
import io
import time
import plotly.graph_objects as go
from cutting_optimizer import optimize_cutting
from utils import create_output_excel, create_accessory_summary, validate_input_excel
import uuid

# Hàm hiển thị mô phỏng cắt thanh
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

# Cấu hình giao diện
st.set_page_config(page_title="Phần mềm Hỗ Trợ Sản Xuất Cửa", layout="wide")
st.title("🤖 Phần mềm Hỗ Trợ Sản Xuất Cửa")

uploaded_file = st.file_uploader("📤 Tải lên tệp Excel dữ liệu", type=["xlsx", "xls"])
if 'result_data' not in st.session_state:
    st.session_state.result_data = None

tab_upload, tab_phu_kien, tab_cat_nhom = st.tabs(["📁 Tải Mẫu Nhập", "📦 Tổng Hợp Phụ Kiện", "✂️ Tối Ưu Cắt Nhôm"])

# Tab Tải Mẫu Nhập
with tab_upload:
    st.subheader("📥 Tải xuống mẫu nhập liệu")
    # Thêm phần giới thiệu và giải thích chức năng
    st.markdown("""
    ### Giới thiệu
    Tab **Tải Mẫu Nhập** cung cấp các mẫu nhập liệu chuẩn để bạn sử dụng trong việc tối ưu hóa cắt nhôm và tổng hợp phụ kiện. Các mẫu này được thiết kế với định dạng cố định, giúp đảm bảo dữ liệu đầu vào chính xác và phù hợp với yêu cầu của phần mềm.

    ### Hướng dẫn sử dụng
    - **Mẫu Cắt Nhôm**: Dùng để nhập dữ liệu cắt nhôm, bao gồm các cột `Mã Thanh`, `Chiều Dài`, `Số Lượng`, và `Mã Cửa` (không bắt buộc). Mẫu này phù hợp để chuẩn bị dữ liệu cho tab **Tối Ưu Cắt Nhôm**.
    - **Mẫu Phụ Kiện**: Dùng để nhập danh sách phụ kiện, bao gồm các cột `Mã phụ kiện`, `Tên phụ phiện`, `Đơn vị tính`, và `Số lượng`. Mẫu này được sử dụng trong tab **Tổng Hợp Phụ Kiện**.
    - **Cách sử dụng**:
      1. Nhấn vào nút **Tải mẫu cắt nhôm** hoặc **Tải mẫu phụ kiện** để tải file mẫu về máy.
      2. Mở file mẫu bằng phần mềm Excel, nhập dữ liệu theo đúng định dạng cột.
      3. Lưu file và tải lên ứng dụng ở các tab tương ứng để xử lý.
    """)
    # Dữ liệu mẫu cho cắt nhôm (giữ cột tiếng Việt)
    nhom_sample = pd.DataFrame({
        'Mã Thanh': ['TNG1', 'TNG2', 'TNG3', 'TNG4'],
        'Chiều Dài': [2000, 1500, 3000, 2500],
        'Số Lượng': [2, 5, 3, 4],
        'Mã Cửa': ['D001', 'D002', 'D003', 'D004']
    })
    out_nhom = io.BytesIO()
    nhom_sample.to_excel(out_nhom, index=False)
    out_nhom.seek(0)
    st.download_button("📄 Tải mẫu cắt nhôm", out_nhom, "mau_cat_nhom.xlsx")

    # Dữ liệu mẫu cho phụ kiện (giữ nguyên)
    pk_sample = pd.DataFrame({
        'Mã phụ kiện': ['PK001', 'PK002', 'PK003', 'PK004'],
        'Tên phụ phiện': ['Gioăng', 'Bulong', 'Đinh vít', 'Ke góc'],
        'Đơn vị tính': ['cái', 'bộ', 'cái', 'bộ'],
        'Số lượng': [15, 25, 50, 10]
    })
    out_pk = io.BytesIO()
    pk_sample.to_excel(out_pk, index=False)
    out_pk.seek(0)
    st.download_button("📄 Tải mẫu phụ kiện", out_pk, "mau_phu_kien.xlsx")

# Tab Tổng Hợp Phụ Kiện
with tab_phu_kien:
    st.subheader("📦 Tổng Hợp Phụ Kiện")
    if uploaded_file:
        try:
            acc_df = pd.read_excel(uploaded_file)
            output = io.BytesIO()
            summary_df = create_accessory_summary(acc_df, output)
            output.seek(0)
            st.success("✅ Tổng hợp thành công!")
            st.dataframe(summary_df)
            st.download_button("📥 Tải Xuống File Tổng Hợp Phụ Kiện", output, "tong_hop_phu_kien.xlsx")
        except Exception as e:
            st.warning("⚠️ File không phù hợp hoặc thiếu cột cần thiết.")

# Tab Tối Ưu Cắt Nhôm
with tab_cat_nhom:
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

                # Gộp các trường nhập liệu vào một hàng với 3 cột
                col1, col2, col3 = st.columns(3)

                with col1:
                    length_text = st.text_input("Nhập kích thước thanh (mm, phân cách bằng dấu phẩy)", "5800, 6000, 6200, 6500")

                with col2:
                    cutting_gap = st.number_input("Khoảng cách cắt (mm)", 1, 100, 10, 1)

                with col3:
                    optimization_method = st.selectbox("Phương pháp tối ưu", ["Tối Ưu Hiệu Suất Cao Nhất", "Tối Ưu Số Lượng Thanh", "Tối Ưu Linh Hoạt"])

                # Nút tối ưu hóa
                if st.button("🚀 Tối Ưu Hóa"):
                    # Chuyển chuỗi kích thước thanh thành danh sách số
                    stock_length_options = [int(x.strip()) for x in length_text.split(",") if x.strip().isdigit()]

                    if not stock_length_options:
                        st.error("Vui lòng nhập ít nhất một kích thước thanh.")
                    else:
                        try:
                            start_time = time.time()
                            result_df, patterns_df, summary_df = optimize_cutting(
                                df,
                                cutting_gap=cutting_gap,
                                optimization_method=optimization_method,
                                stock_length_options=stock_length_options,
                                optimize_stock_length=True
                            )
                            elapsed = time.time() - start_time
                            elapsed_formatted = f"{elapsed:.1f}" if elapsed % 1 != 0 else f"{int(elapsed)}"
                            st.success(f"✅ Hoàn tất trong {elapsed_formatted} giây")
                            st.session_state.result_data = (result_df, patterns_df, summary_df, stock_length_options, cutting_gap)
                        except Exception as opt_err:
                            st.error(f"❌ Lỗi tối ưu hóa: {opt_err}")
        except Exception as e:
            st.error(f"❌ Lỗi xử lý file: {e}")

    # Hiển thị kết quả nếu có
    if st.session_state.result_data:
        result_df, patterns_df, summary_df, stock_length_options, cutting_gap = st.session_state.result_data

        # Đổi tên cột cho bảng tổng hợp và định dạng số thập phân
        st.subheader("📊 Bảng Tổng Hợp Hiệu Suất")
        # Định dạng số thập phân trong bảng hiển thị, hiệu suất dưới dạng phần trăm
        summary_df_display = summary_df.style.format({
            'Hiệu Suất Tổng Thể': "{:.1f}%",
            'Hiệu Suất Trung Bình': "{:.1f}%",
            'Phế Liệu (mm)': lambda x: f"{x:.1f}" if isinstance(x, float) and x % 1 != 0 else f"{int(x)}"
        })
        st.dataframe(summary_df_display)

        # Đổi tên cột cho bảng mẫu cắt và định dạng số thập phân
        st.subheader("📋 Danh Sách Mẫu Cắt")
        # Định dạng số thập phân trong bảng hiển thị, hiệu suất dưới dạng phần trăm
        patterns_df_display = patterns_df.style.format({
            'Hiệu Suất': "{:.1f}%",
            'Chiều Dài Sử Dụng': lambda x: f"{x:.1f}" if isinstance(x, float) and x % 1 != 0 else f"{int(x)}",
            'Chiều Dài Còn Lại': lambda x: f"{x:.1f}" if isinstance(x, float) and x % 1 != 0 else f"{int(x)}"
        })
        st.dataframe(patterns_df_display)

        # Đổi tên cột cho bảng chi tiết mảnh cắt
        result_df = result_df.rename(columns={
            'Item ID': 'Mã Mảnh',
            'Bar Number': 'Số Thanh'
        })
        st.subheader("📄 Bảng Chi Tiết Mảnh Cắt")
        st.dataframe(result_df)

        # Mô phỏng cắt thanh
        st.subheader("📊 Mô Phỏng Cắt Từng Thanh")

        # Khởi tạo biến trong session_state nếu chưa có
        if 'current_profile' not in st.session_state:
            st.session_state.current_profile = None
        if 'page' not in st.session_state:
            st.session_state.page = 0

        # Chọn mã nhôm từ danh sách
        selected_profile = st.selectbox("Chọn Mã Thanh", patterns_df['Mã Thanh'].unique())

        # Kiểm tra và reset trang nếu mã nhôm thay đổi
        if selected_profile != st.session_state.current_profile:
            st.session_state.current_profile = selected_profile
            st.session_state.page = 0  # Reset về trang 1

        # Lọc dữ liệu cho mã nhôm được chọn
        filtered = patterns_df[patterns_df['Mã Thanh'] == selected_profile]

        # Thiết lập phân trang
        rows_per_page = 5
        total_rows = len(filtered)
        num_pages = (total_rows + rows_per_page - 1) // rows_per_page

        # Tính chỉ số dòng hiển thị
        start_idx = st.session_state.page * rows_per_page
        end_idx = min(start_idx + rows_per_page, total_rows)
        display_rows = filtered.iloc[start_idx:end_idx]

        # Hiển thị dữ liệu
        for idx, row in display_rows.iterrows():
            st.markdown(f"**🔹 #{row['Số Thanh']} | {selected_profile} | {int(row['Chiều Dài Thanh'])}mm**")
            display_pattern(row, cutting_gap)

        # Điều hướng trang
        col1, col2 = st.columns(2)
        with col1:
            if st.session_state.page > 0:
                if st.button("Trang trước"):
                    st.session_state.page -= 1
        with col2:
            if st.session_state.page < num_pages - 1:
                if st.button("Trang sau"):
                    st.session_state.page += 1

        # Hiển thị thông tin trang
        st.info(f"Đang hiển thị trang {st.session_state.page + 1}/{num_pages}")

        # Tải xuống kết quả
        output = io.BytesIO()
        create_output_excel(output, result_df, patterns_df, summary_df, stock_length_options, cutting_gap)
        output.seek(0)
        st.download_button("📥 Tải Xuống File Kết Quả Cắt Nhôm", output, "ket_qua_cat_nhom.xlsx")

# Footer
st.markdown("---")
st.markdown("Mọi thắc mắc xin liên hệ Zalo 0977 487 639")
st.markdown("Ứng dụng hỗ trợ sản xuất cửa © 2025")
