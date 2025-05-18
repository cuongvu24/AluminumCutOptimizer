import pandas as pd
import streamlit as st
import io
import time
import plotly.graph_objects as go
from cutting_optimizer import optimize_cutting
from utils import create_output_excel, create_accessory_summary, validate_input_excel, save_optimization_history, load_optimization_history, delete_optimization_history_entry
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

# Giới thiệu ngắn gọn ngay sau tiêu đề
st.markdown("""
**Phần mềm Hỗ Trợ Sản Xuất Cửa** là công cụ hỗ trợ sản xuất cửa nhôm, giúp tối ưu hóa cắt nhôm, quản lý phụ kiện, giảm phế liệu và tăng hiệu suất.  
Hãy chọn tab phù hợp để bắt đầu! Xem hướng dẫn chi tiết trong tab **Giới Thiệu**.
""")

uploaded_file = st.file_uploader("📤 Tải lên tệp Excel dữ liệu", type=["xlsx", "xls"])
if 'result_data' not in st.session_state:
    st.session_state.result_data = None

# Thêm tab "Giới Thiệu" vào danh sách tab
tab_intro, tab_upload, tab_phu_kien, tab_cat_nhom = st.tabs(["📖 Giới Thiệu", "📁 Tải Mẫu Nhập", "📦 Tổng Hợp Phụ Kiện", "✂️ Tối Ưu Cắt Nhôm"])

# Tab Giới Thiệu
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
           - **Tối Ưu Hiệu Suất Cao Nhất**: Chọn kích thước thanh để tối đa hóa hiệu suất sử dụng nguyên liệu (tỷ lệ giữa chiều dài sử dụng và chiều dài thanh).
           - **Tối Ưu Số Lượng Thanh**: Chọn kích thước thanh để sử dụng ít thanh nhất, giảm số lượng thanh cần thiết.
           - **Tối Ưu Linh Hoạt**: Sử dụng nhiều kích thước thanh khác nhau (ví dụ: 5800mm và 6000mm) để giảm thiểu phế liệu, linh hoạt hơn trong việc cắt.
      3. Nhấn nút **"Tối Ưu Hóa"** để chạy tính toán.
      4. Xem kết quả:
         - **Bảng Tổng Hợp Hiệu Suất**: Hiển thị hiệu suất tổng thể, số lượng thanh, và phế liệu của từng mã nhôm.
         - **Danh Sách Mẫu Cắt**: Hiển thị chi tiết mẫu cắt cho từng thanh (kích thước thanh, mẫu cắt, hiệu suất).
         - **Bảng Chi Tiết Mảnh Cắt**: Hiển thị thông tin từng mảnh cắt (mã mảnh, chiều dài, số thanh, mã cửa).
         - **Mô Phỏng Cắt Từng Thanh**: Hiển thị trực quan cách cắt từng thanh, có thể chọn mã nhôm và điều hướng qua các trang.
         - **Lịch Sử Tối Ưu Hóa**: Xem các lần tối ưu hóa trước, tải lại kết quả hoặc xóa lịch sử.
      5. Nhấn **"Tải Xuống File Kết Quả Cắt Nhôm"** để lưu kết quả về máy dưới dạng file Excel.

    ### Lưu ý khi sử dụng
    - Đảm bảo file nhập liệu đúng định dạng theo mẫu được cung cấp, nếu không ứng dụng sẽ báo lỗi.
    - Kích thước thanh và khoảng cách cắt phải là số dương, hợp lý với thực tế sản xuất.
    - Khi sử dụng chế độ "Tối Ưu Linh Hoạt", nên nhập nhiều kích thước thanh để đạt hiệu quả tối ưu nhất.
    """)

# Tab Tải Mẫu Nhập
with tab_upload:
    st.subheader("📥 Tải xuống mẫu nhập liệu")
    st.markdown("""
    👉 Vui lòng sử dụng các mẫu bên dưới để đảm bảo định dạng chính xác khi nhập liệu:
    - **Mẫu Cắt Nhôm** gồm các cột: `Mã Thanh`, `Chiều Dài`, `Số Lượng`, `Mã Cửa` (không bắt buộc)
    - **Mẫu Phụ Kiện** gồm các cột: `Mã phụ kiện`, `Tên phụ phiện`, `Đơn vị tính`, `Số lượng`
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
    
    # Phần lịch sử tối ưu hóa
    st.markdown("### 📜 Lịch Sử Tối Ưu Hóa")
    history_data = load_optimization_history()
    if history_data:
        history_df = pd.DataFrame([
            {
                'ID': entry['id'],
                'Thời Gian': entry['timestamp'],
                'Phương Pháp Tối Ưu': entry['optimization_method'],
                'Mã Thanh': ', '.join(entry['profile_codes']),
                'Kích Thước Thanh': ', '.join(map(str, entry['stock_length_options'])),
                'Khoảng Cách Cắt': entry['cutting_gap']
            }
            for entry in history_data
        ])
        st.dataframe(history_df)
        
        selected_history_id = st.selectbox("Chọn lịch sử để xem chi tiết", [''] + [entry['id'] for entry in history_data])
        if selected_history_id:
            selected_entry = next((entry for entry in history_data if entry['id'] == selected_history_id), None)
            if selected_entry:
                result_df = pd.DataFrame(selected_entry['result_df'])
                patterns_df = pd.DataFrame(selected_entry['patterns_df'])
                summary_df = pd.DataFrame(selected_entry['summary_df'])
                stock_length_options = selected_entry['stock_length_options']
                cutting_gap = selected_entry['cutting_gap']
                
                st.markdown("#### Kết Quả Lịch Sử")
                st.subheader("📊 Bảng Tổng Hợp Hiệu Suất")
                summary_df_display = summary_df.style.format({
                    'Hiệu Suất Tổng Thể': "{:.1f}%",
                    'Hiệu Suất Trung Bình': "{:.1f}%",
                    'Phế Liệu (mm)': lambda x: f"{x:.1f}" if isinstance(x, float) and x % 1 != 0 else f"{int(x)}"
                })
                st.dataframe(summary_df_display)

                st.subheader("📋 Danh Sách Mẫu Cắt")
                patterns_df_display = patterns_df.style.format({
                    'Hiệu Suất': "{:.1f}%",
                    'Chiều Dài Sử Dụng': lambda x: f"{x:.1f}" if isinstance(x, float) and x % 1 != 0 else f"{int(x)}",
                    'Chiều Dài Còn Lại': lambda x: f"{x:.1f}" if isinstance(x, float) and x % 1 != 0 else f"{int(x)}"
                })
                st.dataframe(patterns_df_display)

                st.subheader("📄 Bảng Chi Tiết Mảnh Cắt")
                result_df = result_df.rename(columns={'Item ID': 'Mã Mảnh', 'Bar Number': 'Số Thanh'})
                st.dataframe(result_df)

                st.subheader("📊 Mô Phỏng Cắt Từng Thanh")
                selected_profile = st.selectbox("Chọn Mã Thanh", patterns_df['Mã Thanh'].unique(), key=f"history_profile_{selected_history_id}")
                filtered = patterns_df[patterns_df['Mã Thanh'] == selected_profile]
                for idx, row in filtered.iterrows():
                    st.markdown(f"**🔹 #{row['Số Thanh']} | {selected_profile} | {int(row['Chiều Dài Thanh'])}mm**")
                    display_pattern(row, cutting_gap)

                # Tải xuống kết quả lịch sử
                output = io.BytesIO()
                create_output_excel(output, result_df, patterns_df, summary_df, stock_length_options, cutting_gap)
                output.seek(0)
                st.download_button("📥 Tải Xuống Kết Quả Lịch Sử", output, f"ket_qua_cat_nhom_{selected_entry['timestamp'].replace(':', '-')}.xlsx")
                
                # Nút xóa lịch sử
                if st.button("🗑️ Xóa Lịch Sử Này"):
                    delete_optimization_history_entry(selected_history_id)
                    st.success("✅ Đã xóa lịch sử!")
                    st.experimental_rerun()
    else:
        st.info("ℹ️ Chưa có lịch sử tối ưu hóa.")

    # Phần tối ưu hóa mới
    st.markdown("### ✂️ Tối Ưu Hóa Mới")
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
                    optimization_method = st.selectbox("Phương pháp tối ưu", ["Tối Ưu Hiệu Suất Cao Nhất", "Tối Ưu Số Lượng Thanh", "Tối Ưu Linh Hoạt", "Tối Ưu PuLP"])

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
                            
                            # Lưu vào lịch sử
                            save_optimization_history(
                                result_df, patterns_df, summary_df, stock_length_options, cutting_gap, optimization_method
                            )
                        except Exception as opt_err:
                            st.error(f"❌ Lỗi tối ưu hóa: {opt_err}")
        except Exception as e:
            st.error(f"❌ Lỗi xử lý file: {e}")

    # Hiển thị kết quả nếu có
    if st.session_state.result_data:
        result_df, patterns_df, summary_df, stock_length_options, cutting_gap = st.session_state.result_data

        # Đổi tên cột cho bảng tổng hợp và định dạng số thập phân
        st.subheader("📊 Bảng Tổng Hợp Hiệu Suất")
        summary_df_display = summary_df.style.format({
            'Hiệu Suất Tổng Thể': "{:.1f}%",
            'Hiệu Suất Trung Bình': "{:.1f}%",
            'Phế Liệu (mm)': lambda x: f"{x:.1f}" if isinstance(x, float) and x % 1 != 0 else f"{int(x)}"
        })
        st.dataframe(summary_df_display)

        # Đổi tên cột cho bảng mẫu cắt và định dạng số thập phân
        st.subheader("📋 Danh Sách Mẫu Cắt")
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
