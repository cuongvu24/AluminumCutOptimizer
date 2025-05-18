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
import json

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

# Hàm đếm ngược thời gian
def countdown_placeholder(placeholder, max_time):
    for i in range(max_time, -1, -1):
        placeholder.markdown(f"⏳ **Đang tối ưu hóa... Còn {i} giây**")
        time.sleep(1)

# Cấu hình giao diện
st.set_page_config(page_title="Phần mềm Hỗ Trợ Sản Xuất Cửa", layout="wide")
st.title("🤖 Phần mềm Hỗ Trợ Sản Xuất Cửa")

# CSS để bảng và thông báo full chiều rộng
st.markdown("""
<style>
    .stDataFrame, .stAlert {
        width: 100%;
        border: 1px solid #ddd;
        border-radius: 5px;
        overflow-x: auto;
        margin: 10px auto;
        padding: 10px;
    }
    .stDataFrame table {
        width: 100%;
        table-layout: auto;
    }
    .stDataFrame th, .stDataFrame td {
        padding: 8px;
        text-align: left;
    }
    .stAlert > div {
        padding: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Giới thiệu ngắn gọn ngay sau tiêu đề
st.markdown("""
**Phần mềm Hỗ Trợ Sản Xuất Cửa** là công cụ hỗ trợ sản xuất cửa nhôm, giúp tối ưu hóa cắt nhôm, quản lý phụ kiện, giảm phế liệu và tăng hiệu suất.  
Hãy chọn tab phù hợp để bắt đầu! Xem hướng dẫn chi tiết trong tab **Giới Thiệu**.
""")

uploaded_file = st.file_uploader("📤 Tải lên tệp Excel dữ liệu", type=["xlsx", "xls"])
if 'result_data' not in st.session_state:
    st.session_state.result_data = None

# Các tab chính
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

# Tab Tải Mẫu Nhập
with tab_upload:
    st.subheader("📥 Tải xuống mẫu nhập liệu")
    st.markdown("""
    👉 Vui lòng sử dụng các mẫu bên dưới để đảm bảo định dạng chính xác:
    - **Mẫu Cắt Nhôm**: `Mã Thanh`, `Chiều Dài`, `Số Lượng`, `Mã Cửa` (không bắt buộc)
    - **Mẫu Phụ Kiện**: `Mã phụ kiện`, `Tên phụ phiện`, `Đơn vị tính`, `Số lượng`
    """)
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
            st.dataframe(summary_df, use_container_width=True)
            st.download_button("📥 Tải Xuống File Tổng Hợp Phụ Kiện", output, "tong_hop_phu_kien.xlsx")
        except Exception as e:
            st.warning("⚠️ File không phù hợp hoặc thiếu cột cần thiết.")

# Tab Tối Ưu Cắt Nhôm
with tab_cat_nhom:
    st.subheader("✂️ Tối Ưu Hóa Cắt Nhôm")
    
    # Tạo sub-tabs trong Tối Ưu Cắt Nhôm
    subtab_new, subtab_history = st.tabs(["Tối Ưu Hóa Mới", "Lịch Sử Tối Ưu Hóa"])
    
    # Sub-tab Lịch Sử Tối Ưu Hóa
    with subtab_history:
        st.markdown("### 📜 Lịch Sử Tối Ưu Hóa")
        history_data = load_optimization_history()
        if history_data:
            # Tạo bảng lịch sử không có cột STT
            history_df = pd.DataFrame([
                {
                    'Tên': entry.get('name', entry['timestamp']),
                    'Thời Gian': entry['timestamp'],
                    'Phương Pháp Tối Ưu': entry['optimization_method'],
                    'Mã Thanh': ', '.join(entry['profile_codes']),
                    'Kích Thước Thanh': ', '.join(map(str, entry['stock_length_options'])),
                    'Khoảng Cách Cắt': entry['cutting_gap']
                }
                for entry in history_data
            ])
            st.dataframe(history_df, use_container_width=True)
            
            # Chọn lịch sử bằng tên
            history_names = [''] + [entry.get('name', entry['timestamp']) for entry in history_data]
            selected_history_name = st.selectbox("Chọn lịch sử để xem chi tiết", history_names)
            if selected_history_name:
                # Tìm entry dựa trên tên
                selected_entry = next((entry for entry in history_data if entry.get('name', entry['timestamp']) == selected_history_name), None)
                if selected_entry:
                    result_df = pd.DataFrame(selected_entry['result_df'])
                    patterns_df = pd.DataFrame(selected_entry['patterns_df'])
                    summary_df = pd.DataFrame(selected_entry['summary_df'])
                    stock_length_options = selected_entry['stock_length_options']
                    cutting_gap = selected_entry['cutting_gap']
                    
                    # Cho phép chỉnh sửa tên lịch sử
                    current_name = selected_entry.get('name', selected_entry['timestamp'])
                    new_name = st.text_input("Đặt tên cho lịch sử này", value=current_name, key=f"name_{selected_entry['id']}")
                    if new_name != current_name:
                        history_data = [entry for entry in history_data if entry['id'] != selected_entry['id']]
                        selected_entry['name'] = new_name
                        with open("history.json", 'w', encoding='utf-8') as f:
                            json.dump(history_data, f, ensure_ascii=False, indent=2)
                        st.success("✅ Đã cập nhật tên lịch sử!")
                        st.rerun()  # Làm mới giao diện để hiển thị tên mới
                    
                    st.markdown("#### Kết Quả Lịch Sử")
                    st.subheader("📊 Bảng Tổng Hợp Hiệu Suất")
                    summary_df_display = summary_df.style.format({
                        'Hiệu Suất Tổng Thể': "{:.1f}%",
                        'Hiệu Suất Trung Bình': "{:.1f}%",
                        'Phế Liệu (mm)': lambda x: f"{x:.1f}" if isinstance(x, float) and x % 1 != 0 else f"{int(x)}"
                    })
                    st.dataframe(summary_df_display, use_container_width=True)

                    st.subheader("📋 Danh Sách Mẫu Cắt")
                    patterns_df_display = patterns_df.style.format({
                        'Hiệu Suất': "{:.1f}%",
                        'Chiều Dài Sử Dụng': lambda x: f"{x:.1f}" if isinstance(x, float) and x % 1 != 0 else f"{int(x)}",
                        'Chiều Dài Còn Lại': lambda x: f"{x:.1f}" if isinstance(x, float) and x % 1 != 0 else f"{int(x)}"
                    })
                    st.dataframe(patterns_df_display, use_container_width=True)

                    st.subheader("📄 Bảng Chi Tiết Mảnh Cắt")
                    result_df = result_df.rename(columns={'Item ID': 'Mã Mảnh', 'Bar Number': 'Số Thanh'})
                    st.dataframe(result_df, use_container_width=True)

                    st.subheader("📊 Mô Phỏng Cắt Từng Thanh")
                    selected_profile = st.selectbox("Chọn Mã Thanh", patterns_df['Mã Thanh'].unique(), key=f"history_profile_{selected_entry['id']}")
                    filtered = patterns_df[patterns_df['Mã Thanh'] == selected_profile]
                    rows_per_page = 5
                    total_rows = len(filtered)
                    num_pages = (total_rows + rows_per_page - 1) // rows_per_page
                    page_key = f"history_page_{selected_entry['id']}"
                    if page_key not in st.session_state:
                        st.session_state[page_key] = 0

                    start_idx = st.session_state[page_key] * rows_per_page
                    end_idx = min(start_idx + rows_per_page, total_rows)
                    display_rows = filtered.iloc[start_idx:end_idx]

                    for idx, row in display_rows.iterrows():
                        st.markdown(f"**🔹 #{row['Số Thanh']} | {selected_profile} | {int(row['Chiều Dài Thanh'])}mm**")
                        display_pattern(row, cutting_gap)

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.session_state[page_key] > 0:
                            if st.button("Trang trước", key=f"prev_{selected_entry['id']}"):
                                st.session_state[page_key] -= 1
                    with col2:
                        if st.session_state[page_key] < num_pages - 1:
                            if st.button("Trang sau", key=f"next_{selected_entry['id']}"):
                                st.session_state[page_key] += 1

                    st.info(f"Đang hiển thị trang {st.session_state[page_key] + 1}/{num_pages}")

                    # Tải xuống kết quả lịch sử
                    output = io.BytesIO()
                    create_output_excel(output, result_df, patterns_df, summary_df, stock_length_options, cutting_gap)
                    output.seek(0)
                    st.download_button("📥 Tải Xuống Kết Quả Lịch Sử", output, f"ket_qua_cat_nhom_{selected_entry['timestamp'].replace(':', '-')}.xlsx")
                    
                    # Nút xóa lịch sử
                    if st.button("🗑️ Xóa Lịch Sử Này"):
                        delete_optimization_history_entry(selected_entry['id'])
                        st.success("✅ Đã xóa lịch sử!")
                        st.rerun()
        else:
            st.info("ℹ️ Chưa có lịch sử tối ưu hóa.")

    # Sub-tab Tối Ưu Hóa Mới
    with subtab_new:
        st.markdown("### ✂️ Tối Ưu Hóa Mới")
        if uploaded_file:
            try:
                df = pd.read_excel(uploaded_file)
                valid, message = validate_input_excel(df)
                if not valid:
                    st.error(message)
                else:
                    st.success("✅ Dữ liệu nhôm hợp lệ!")
                    st.dataframe(df, use_container_width=True)

                    col1, col2, col3 = st.columns(3)

                    with col1:
                        length_text = st.text_input("Nhập kích thước thanh (mm, phân cách bằng dấu phẩy)", "5800, 6000, 6200, 6500")

                    with col2:
                        cutting_gap = st.number_input("Khoảng cách cắt (mm)", 1, 100, 10, 1)

                    with col3:
                        optimization_method = st.selectbox("Phương pháp tối ưu", ["Tối Ưu Hiệu Suất Cao Nhất", "Tối Ưu Số Lượng Thanh", "Tối Ưu Linh Hoạt", "Tối Ưu PuLP"])

                    # Thêm trường nhập tên cho lần tối ưu hóa
                    history_name = st.text_input("Tên cho lần tối ưu hóa này", value=f"Tối ưu hóa {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

                    # Nút tối ưu hóa
                    if st.button("🚀 Tối Ưu Hóa"):
                        stock_length_options = [int(x.strip()) for x in length_text.split(",") if x.strip().isdigit()]

                        if not stock_length_options:
                            st.error("Vui lòng nhập ít nhất một kích thước thanh.")
                        else:
                            try:
                                start_time = time.time()
                                max_time = 30  # Thời gian tối đa 30 giây
                                placeholder = st.empty()
                                countdown_thread = threading.Thread(target=countdown_placeholder, args=(placeholder, max_time))
                                countdown_thread.start()

                                result_df, patterns_df, summary_df = optimize_cutting(
                                    df,
                                    cutting_gap=cutting_gap,
                                    optimization_method=optimization_method,
                                    stock_length_options=stock_length_options,
                                    optimize_stock_length=True
                                )

                                countdown_thread.join()
                                placeholder.empty()
                                elapsed = time.time() - start_time
                                elapsed_formatted = f"{elapsed:.1f}" if elapsed % 1 != 0 else f"{int(elapsed)}"
                                st.success(f"✅ Hoàn tất trong {elapsed_formatted} giây")
                                st.session_state.result_data = (result_df, patterns_df, summary_df, stock_length_options, cutting_gap)
                                
                                # Lưu vào lịch sử với tên
                                save_optimization_history(
                                    result_df, patterns_df, summary_df, stock_length_options, cutting_gap, optimization_method, name=history_name
                                )
                                st.rerun()  # Làm mới giao diện để hiển thị lịch sử mới
                            except Exception as opt_err:
                                placeholder.empty()
                                st.error(f"❌ Lỗi tối ưu hóa: {opt_err}")
            except Exception as e:
                st.error(f"❌ Lỗi xử lý file: {e}")
        else:
            st.info("Vui lòng tải lên tệp Excel để bắt đầu tối ưu hóa.")

        # Hiển thị kết quả nếu có
        if st.session_state.result_data:
            result_df, patterns_df, summary_df, stock_length_options, cutting_gap = st.session_state.result_data

            st.subheader("📊 Bảng Tổng Hợp Hiệu Suất")
            summary_df_display = summary_df.style.format({
                'Hiệu Suất Tổng Thể': "{:.1f}%",
                'Hiệu Suất Trung Bình': "{:.1f}%",
                'Phế Liệu (mm)': lambda x: f"{x:.1f}" if isinstance(x, float) and x % 1 != 0 else f"{int(x)}"
            })
            st.dataframe(summary_df_display, use_container_width=True)

            st.subheader("📋 Danh Sách Mẫu Cắt")
            patterns_df_display = patterns_df.style.format({
                'Hiệu Suất': "{:.1f}%",
                'Chiều Dài Sử Dụng': lambda x: f"{x:.1f}" if isinstance(x, float) and x % 1 != 0 else f"{int(x)}",
                'Chiều Dài Còn Lại': lambda x: f"{x:.1f}" if isinstance(x, float) and x % 1 != 0 else f"{int(x)}"
            })
            st.dataframe(patterns_df_display, use_container_width=True)

            st.subheader("📄 Bảng Chi Tiết Mảnh Cắt")
            result_df = result_df.rename(columns={
                'Item ID': 'Mã Mảnh',
                'Bar Number': 'Số Thanh'
            })
            st.dataframe(result_df, use_container_width=True)

            st.subheader("📊 Mô Phỏng Cắt Từng Thanh")
            if 'current_profile' not in st.session_state:
                st.session_state.current_profile = None
            if 'page' not in st.session_state:
                st.session_state.page = 0

            selected_profile = st.selectbox("Chọn Mã Thanh", patterns_df['Mã Thanh'].unique())
            if selected_profile != st.session_state.current_profile:
                st.session_state.current_profile = selected_profile
                st.session_state.page = 0

            filtered = patterns_df[patterns_df['Mã Thanh'] == selected_profile]
            rows_per_page = 5
            total_rows = len(filtered)
            num_pages = (total_rows + rows_per_page - 1) // rows_per_page

            start_idx = st.session_state.page * rows_per_page
            end_idx = min(start_idx + rows_per_page, total_rows)
            display_rows = filtered.iloc[start_idx:end_idx]

            for idx, row in display_rows.iterrows():
                st.markdown(f"**🔹 #{row['Số Thanh']} | {selected_profile} | {int(row['Chiều Dài Thanh'])}mm**")
                display_pattern(row, cutting_gap)

            col1, col2 = st.columns(2)
            with col1:
                if st.session_state.page > 0:
                    if st.button("Trang trước"):
                        st.session_state.page -= 1
            with col2:
                if st.session_state.page < num_pages - 1:
                    if st.button("Trang sau"):
                        st.session_state.page += 1

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
