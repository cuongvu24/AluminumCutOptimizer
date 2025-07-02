import pandas as pd
import streamlit as st
import io
import time
import plotly.graph_objects as go
from cutting_optimizer import optimize_cutting
from utils import create_output_excel, create_accessory_summary, validate_input_excel, save_optimization_history, load_optimization_history, delete_optimization_history_entry
import uuid
from datetime import datetime
import threading

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

tab_intro, tab_upload, tab_pk, tab_cut = st.tabs(["📖 Giới Thiệu", "📁 Tải Mẫu", "📦 Phụ Kiện", "✂️ Tối Ưu Cắt"])

# ============== Tab Giới Thiệu Và Hướng Dẫn Sử Dụng ==============
with tab_intro:
    st.subheader("📖 Giới Thiệu và Hướng Dẫn Sử Dụng")
    st.markdown("""
    ### Giới thiệu
    **Phần mềm Hỗ Trợ Sản Xuất Cửa** là một công cụ hỗ trợ sản xuất cửa nhôm, giúp tối ưu hóa quy trình cắt nhôm và quản lý phụ kiện. Ứng dụng được thiết kế để giảm thiểu phế liệu, tiết kiệm thời gian, và tăng hiệu quả sản xuất thông qua các tính năng thông minh và dễ sử dụng.

    ### Hướng dẫn sử dụng các chức năng

    #### 1. 📁 Tải Mẫu Nhập
    - **Chức năng**: Cung cấp các mẫu nhập liệu chuẩn để người dùng nhập dữ liệu cho việc tối ưu hóa cắt nhôm và tổng hợp phụ kiện.
    - **Hướng dẫn sử dụng**:
      1. Nhấn vào nút **"Tải mẫu cắt nhôm"** hoặc **"Tải mẫu phụ kiện"** để tải file mẫu về máy.
      2. Mở file mẫu bằng phần mềm Excel và nhập dữ liệu theo đúng định dạng cột:
         - **Mẫu Cắt Nhôm**: Bao gồm các cột `Mã Thanh`, `Chiều Dài`, `Số Lượng`, `Mã Cửa` (không bắt buộc).
         - **Mẫu Phụ Kiện**: Bao gồm các cột `Mã phụ kiện`, `Tên phụ phiện`, `Đơn vị tính`, `Số lượng`.
      3. Lưu file và sử dụng ở các tab tương ứng (Tổng Hợp Phụ Kiện hoặc Tối Ưu Cắt Nhôm).

    #### 2. 📦 Tổng Hợp Phụ Kiện
    - **Chức năng**: Tổng hợp số lượng phụ kiện cần thiết dựa trên file danh sách phụ kiện mà người dùng tải lên.
    - **Hướng dẫn sử dụng**:
      1. Tải file phụ kiện (đã nhập liệu theo mẫu) bằng cách kéo thả hoặc chọn file từ máy.
      2. Ứng dụng sẽ tự động tổng hợp số lượng theo từng loại phụ kiện và hiển thị bảng kết quả.
      3. Nhấn **"Tải Xuống File Tổng Hợp Phụ Kiện"** để lưu kết quả về máy dưới dạng file Excel.

    #### 3. ✂️ Tối Ưu Cắt Nhôm
    - **Chức năng**: Tối ưu hóa việc cắt nhôm để giảm phế liệu và tăng hiệu suất, hỗ trợ nhiều phương pháp tối ưu và tùy chỉnh khoảng cách cắt.
    - **Hướng dẫn sử dụng**:
      1. Tải file cắt nhôm (đã nhập liệu theo mẫu) bằng cách kéo thả hoặc chọn file từ máy.
      2. Nhập các thông số cần thiết:
         - **Kích thước thanh**: Nhập các kích thước thanh có sẵn (mm), phân cách bằng dấu phẩy (ví dụ: 5800, 6000).
         - **Khoảng cách cắt**: Nhập khoảng cách giữa các mảnh cắt trên thanh (mm), thường do lưỡi cắt tạo ra (mặc định: 10mm, có thể điều chỉnh từ 1-100mm). Khoảng cách này ảnh hưởng đến tính toán phế liệu và hiệu suất.
         - **Phương pháp tối ưu**:
           - **Tối Ưu Hiệu Suất Cao Nhất**: Chọn kích thước thanh để tối đa hóa hiệu suất sử dụng nguyên liệu.
           - **Tối Ưu Số Lượng Thanh**: Chọn kích thước thanh để sử dụng ít thanh nhất.
           - **Tối Ưu Linh Hoạt**: Sử dụng nhiều kích thước thanh để giảm thiểu phế liệu.
           - **Tối Ưu PuLP**: Sử dụng lập trình tuyến tính với PuLP (chuyển sang Tối Ưu Linh Hoạt nếu dữ liệu lớn).
      3. Nhấn nút **"Tối Ưu Hóa"** để chạy tính toán.
      4. Xem kết quả:
         - **Bảng Tổng Hợp Hiệu Suất**: Hiển thị hiệu suất tổng thể, số lượng thanh, và phế liệu.
         - **Danh Sách Mẫu Cắt**: Hiển thị chi tiết mẫu cắt cho từng thanh.
         - **Bảng Chi Tiết Mảnh Cắt**: Hiển thị thông tin từng mảnh cắt.
         - **Mô Phỏng Cắt Từng Thanh**: Hiển thị trực quan cách cắt từng thanh.
         - **Lịch Sử Tối Ưu Hóa**: Xem, đổi tên, hoặc xóa các lần tối ưu hóa trước.
      5. Nhấn **"Tải Xuống File Kết Quả Cắt Nhôm"** để lưu kết quả.

    ### Lưu ý khi sử dụng
    - Đảm bảo file nhập liệu đúng định dạng theo mẫu.
    - Kích thước thanh và khoảng cách cắt phải là số dương.
    - Phương pháp "Tối Ưu PuLP" sẽ tự động chuyển sang "Tối Ưu Linh Hoạt" nếu dữ liệu quá lớn (>100 mục mỗi mã thanh).
    """)
# ============== Tab Tải Mẫu ==============
with tab_upload:
    st.header("📁 Tải Mẫu Nhập")
    st.markdown("""
    👉 Tải mẫu chuẩn:
    - **Mẫu Cắt Nhôm**: `Mã Thanh`, `Chiều Dài`, `Số Lượng`, `Mã Cửa` (tùy chọn)
    - **Mẫu Phụ Kiện**: `Mã phụ kiện`, `Tên phụ phiện`, `Đơn vị tính`, `Số lượng`
    """)
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
            st.dataframe(summary)
            st.download_button("📥 Tải File Phụ Kiện", output, "tong_hop_phu_kien.xlsx")
        except:
            st.warning("⚠️ Không phải file phụ kiện hoặc thiếu cột!")


# ============== Tab Tối Ưu Cắt Nhôm ==============
with tab_cut:
    st.header("✂️ Tối Ưu Hóa Cắt Nhôm")
    if uploaded_file:
        try:
            df = pd.read_excel(uploaded_file)
            valid, msg = validate_input_excel(df)
            if not valid:
                st.error(msg)
            else:
                st.success("✅ File cắt nhôm hợp lệ.")
                st.dataframe(df)
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
                            st.session_state.result_data = (result_df, patterns_df, summary_df, stock_lengths, gap)
                            elapsed = time.time() - start
                            st.success(f"✅ Xong sau {elapsed:.1f}s")
                        except Exception as e:
                            st.error(f"Lỗi tối ưu: {e}")
        except Exception as e:
            st.error(f"Lỗi: {e}")
    else:
        st.info("📤 Vui lòng tải file trước!")

    # ✅ Ngoài `try`
    if st.session_state.result_data:
        result_df, patterns_df, summary_df, stock_lengths, gap = st.session_state.result_data
        st.subheader("📊 Hiệu Suất")
        st.dataframe(summary_df)
        st.subheader("📋 Mẫu Cắt")
        st.dataframe(patterns_df)
        st.subheader("📄 Chi Tiết Mảnh")
        st.dataframe(result_df)

        st.subheader("📊 Mô Phỏng")
        selected_profile = st.selectbox("Chọn Mã Thanh", patterns_df['Mã Thanh'].unique())
        filtered = patterns_df[patterns_df['Mã Thanh'] == selected_profile]
        for idx, row in filtered.iterrows():
            st.markdown(f"🔹 #{row['Số Thanh']} | {selected_profile} | {row['Chiều Dài Thanh']}mm")
            display_pattern(row, gap)

        out = io.BytesIO()
        create_output_excel(out, result_df, patterns_df, summary_df, stock_lengths, gap)
        out.seek(0)
        st.download_button("📥 Tải File Kết Quả", out, "ket_qua_cat_nhom.xlsx")
