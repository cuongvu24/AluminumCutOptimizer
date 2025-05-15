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

# App title and description
st.title("✂️ Phần Mềm Tối Ưu Cắt Nhôm")
st.markdown("[📦 Xem mã nguồn trên GitHub](https://github.com/hero9xhn/AluminumCutOptimizer)")
st.markdown("""
Phần mềm này giúp tối ưu hóa các mẫu cắt nhôm để giảm thiểu lãng phí. Tải lên file Excel
với thông tin các thanh nhôm và kích thước, và nhận kế hoạch cắt tối ưu với số liệu chi tiết.
""")

# Input file guidelines
st.subheader("Hướng Dẫn File Đầu Vào")
st.markdown("""
File Excel của bạn nên chứa các cột sau:
1. **Mã Thanh** - Mã/model của thanh nhôm
2. **Chiều Dài** - Chiều dài yêu cầu của mỗi thanh (mm)
3. **Số Lượng** - Số lượng cần thiết cho mỗi thanh

Chiều dài tiêu chuẩn cho các thanh nhôm và khoảng cách cắt có thể được chỉ định bên dưới.
""")

# Parameters for optimization
col1, col2, col3 = st.columns(3)
with col1:
    stock_length = st.number_input("Chiều Dài Tiêu Chuẩn (mm)", min_value=1000, value=6000, step=100)
with col2:
    cutting_gap = st.number_input("Khoảng Cách Cắt (mm)", min_value=1, value=10, step=1)
with col3:
    optimization_method = st.selectbox(
        "Phương Pháp Tối Ưu", 
        ["Tối Ưu Hiệu Suất Cao Nhất", "Tối Ưu Số Lượng Thanh"]
    )

# Stock length options
optimization_options = st.radio(
    "Tùy Chọn Tối Ưu Kích Thước Thanh",
    ["Sử Dụng Chiều Dài Cố Định", "Tối Ưu Trong Các Giá Trị Cố Định", "Tối Ưu Trong Khoảng Giá Trị"]
)

if optimization_options == "Sử Dụng Chiều Dài Cố Định":
    stock_length_options = [stock_length]
    optimize_stock_length = False
    st.info(f"Sử dụng chiều dài cố định {stock_length}mm")
    
elif optimization_options == "Tối Ưu Trong Các Giá Trị Cố Định":
    st.info("Hệ thống sẽ phân tích và đề xuất kích thước thanh tối ưu từ các lựa chọn")
    
    # Tạo danh sách kích thước có sẵn mặc định
    default_lengths = [3000, 4000, 5000, 5500, 6000, 6500, 7000, 8000]
    
    # Tùy chỉnh độ dài thanh có sẵn
    custom_option = st.checkbox("Tùy chỉnh danh sách kích thước thanh có sẵn", value=False)
    
    if custom_option:
        # Nhập text để tùy chỉnh
        custom_lengths_text = st.text_area(
            "Nhập các kích thước thanh có sẵn (mm), mỗi kích thước một dòng hoặc cách nhau bởi dấu phẩy:",
            value="3000\n4000\n5000\n5500\n6000\n6500\n7000\n8000"
        )
        
        # Xử lý input
        if "," in custom_lengths_text:
            # Nếu người dùng nhập theo dạng phân cách bằng dấu phẩy
            custom_lengths_raw = custom_lengths_text.split(",")
        else:
            # Nếu người dùng nhập mỗi số một dòng
            custom_lengths_raw = custom_lengths_text.split("\n")
        
        # Chuyển đổi thành số và loại bỏ các giá trị không hợp lệ
        available_lengths = []
        for length_str in custom_lengths_raw:
            length_str = length_str.strip()
            if length_str and length_str.isdigit():
                available_lengths.append(int(length_str))
        
        if not available_lengths:
            st.error("Vui lòng nhập ít nhất một kích thước hợp lệ")
            available_lengths = default_lengths
    else:
        available_lengths = default_lengths
    
    # Hiển thị multiselect với danh sách đã được tùy chỉnh
    stock_length_options = st.multiselect(
        "Các Kích Thước Thanh Có Sẵn (mm)",
        options=available_lengths,
        default=[6000]
    )
    
    if not stock_length_options:
        st.warning("Vui lòng chọn ít nhất một kích thước thanh")
        stock_length_options = [6000]
        
    optimize_stock_length = True
    
else:  # "Tối Ưu Trong Khoảng Giá Trị"
    st.info("Hệ thống sẽ phân tích trong khoảng giá trị để tìm kích thước thanh tối ưu")
    col1, col2, col3 = st.columns(3)
    with col1:
        min_length = st.number_input("Chiều Dài Tối Thiểu (mm)", min_value=1000, value=5500, step=100)
    with col2:
        max_length = st.number_input("Chiều Dài Tối Đa (mm)", min_value=1000, value=6500, step=100)
    with col3:
        step_length = st.number_input("Biên Độ Thay Đổi (mm)", min_value=100, value=100, step=100)
    
    # Tạo danh sách các kích thước trong khoảng đã cho
    stock_length_options = list(range(int(min_length), int(max_length) + int(step_length), int(step_length)))
    optimize_stock_length = True
    st.write(f"Sẽ tối ưu trong các kích thước: {', '.join([str(x) for x in stock_length_options])}mm")

# File upload
uploaded_file = st.file_uploader("Tải Lên File Excel", type=["xlsx", "xls"])

if uploaded_file is not None:
    # Read and validate the uploaded file
    try:
        input_data = pd.read_excel(uploaded_file)
        
        # Validate the input data structure
        validation_result, message = validate_input_excel(input_data)
        
        if not validation_result:
            st.error(message)
        else:
            st.success("File tải lên hợp lệ!")
            
            # Display input data
            st.subheader("Dữ Liệu Đầu Vào")
            st.dataframe(input_data)
            
            # Run optimization process
            with st.spinner("Đang tối ưu hóa mẫu cắt..."):
                # Start optimization calculation
                start_time = time.time()
                result_df, patterns_df, summary_df = optimize_cutting(
                    input_data, 
                    stock_length, 
                    cutting_gap,
                    optimization_method=optimization_method,
                    stock_length_options=stock_length_options,
                    optimize_stock_length=optimize_stock_length
                )
                end_time = time.time()
                
                st.success(f"Tối ưu hóa hoàn tất trong {end_time - start_time:.2f} giây!")
            
            # Display summary statistics
            st.subheader("Tổng Hợp Tối Ưu")
            
            # Format summary dataframe with Vietnamese column names
            summary_display = summary_df.copy()
            summary_display.columns = [
                'Mã Thanh', 
                'Tổng Số Thanh', 
                'Tổng Thanh Sử Dụng', 
                'Tổng Chiều Dài Cần (mm)', 
                'Tổng Chiều Dài Nguyên Liệu (mm)', 
                'Phế Liệu (mm)', 
                'Hiệu Suất Tổng Thể', 
                'Hiệu Suất Trung Bình'
            ]
            summary_display['Hiệu Suất Tổng Thể'] = summary_display['Hiệu Suất Tổng Thể'].apply(lambda x: f"{x*100:.2f}%")
            summary_display['Hiệu Suất Trung Bình'] = summary_display['Hiệu Suất Trung Bình'].apply(lambda x: f"{x*100:.2f}%")
            
            st.dataframe(summary_display)
            
            # Display detailed results
            st.subheader("Mẫu Cắt Chi Tiết")
            
            # Format patterns dataframe with Vietnamese column names
            patterns_display = patterns_df.copy()
            patterns_display.columns = [
                'Mã Thanh', 
                'Số Thanh', 
                'Chiều Dài Tiêu Chuẩn', 
                'Chiều Dài Sử Dụng', 
                'Chiều Dài Còn Lại', 
                'Hiệu Suất', 
                'Mẫu Cắt', 
                'Số Mảnh'
            ]
            patterns_display['Hiệu Suất'] = patterns_display['Hiệu Suất'].apply(lambda x: f"{x*100:.2f}%")
            
            st.dataframe(patterns_display)
            
            # Visualize cutting patterns
            st.subheader("Hình Ảnh Mẫu Cắt")
            profile_codes = patterns_df['Profile Code'].unique()
            
            selected_profile = st.selectbox("Chọn Mã Thanh để Hiển Thị", profile_codes)
            
            # Filter patterns for the selected profile
            profile_patterns = patterns_df[patterns_df['Profile Code'] == selected_profile]
            
            for idx, row in profile_patterns.iterrows():
                pattern = row['Cutting Pattern']
                pattern_parts = pattern.split('+')
                
                # Create visualization
                fig = go.Figure()
                
                # Get stock length for this pattern
                current_stock_length = row['Stock Length']
                
                # Draw the full bar
                fig.add_shape(
                    type="rect",
                    x0=0,
                    y0=0,
                    x1=current_stock_length,
                    y1=1,
                    line=dict(color="LightGrey"),
                    fillcolor="LightGrey",
                )
                
                # Draw the pieces
                current_pos = 0
                for part in pattern_parts:
                    if part.strip():  # Skip empty parts
                        part_length = float(part.strip())
                        if part_length > 0:  # Skip zero-length parts
                            fig.add_shape(
                                type="rect",
                                x0=current_pos,
                                y0=0,
                                x1=current_pos + part_length,
                                y1=1,
                                line=dict(color="RoyalBlue"),
                                fillcolor="RoyalBlue",
                            )
                            # Add text label
                            fig.add_annotation(
                                x=(current_pos + current_pos + part_length) / 2,
                                y=0.5,
                                text=f"{part_length}",
                                showarrow=False,
                                font=dict(color="white")
                            )
                            current_pos += part_length + cutting_gap
                
                # Calculate remaining length
                remaining = current_stock_length - current_pos + cutting_gap  # Add back the last cutting gap
                if remaining > 0:
                    fig.add_shape(
                        type="rect",
                        x0=current_pos,
                        y0=0,
                        x1=current_stock_length,
                        y1=1,
                        line=dict(color="Crimson"),
                        fillcolor="Crimson",
                    )
                    # Add text label for remaining
                    fig.add_annotation(
                        x=(current_pos + current_stock_length) / 2,
                        y=0.5,
                        text=f"Còn lại: {remaining}",
                        showarrow=False,
                        font=dict(color="white")
                    )
                
                # Update layout
                fig.update_layout(
                    title=f"Thanh #{row['Bar Number']} - Hiệu suất: {row['Efficiency']*100:.2f}% - Chiều dài: {current_stock_length}mm",
                    xaxis=dict(title="Chiều dài (mm)"),
                    yaxis=dict(showticklabels=False),
                    height=150,
                    margin=dict(l=20, r=20, t=40, b=20),
                )
                
                st.plotly_chart(fig, use_container_width=True)
            
            # Generate downloadable Excel with the results
            output = io.BytesIO()
            create_output_excel(output, result_df, patterns_df, summary_df, stock_length, cutting_gap)
            output.seek(0)
            
            st.download_button(
                label="Tải Xuống Kết Quả Tối Ưu",
                data=output,
                file_name="ket_qua_toi_uu_cat_nhom.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
    except Exception as e:
        st.error(f"Lỗi xử lý tệp: {str(e)}")

# Add example template for download
st.subheader("Cần mẫu biểu mẫu?")
st.markdown("Tải xuống mẫu để xem định dạng yêu cầu:")

# Create a sample DataFrame
sample_data = {
    'Mã Thanh': ['ALU001', 'ALU001', 'ALU001', 'ALU002', 'ALU002'],
    'Chiều Dài': [1200, 800, 1500, 2000, 1000],
    'Số Lượng': [5, 3, 2, 4, 6]
}
sample_df = pd.DataFrame(sample_data)
# Rename columns to match expected input
sample_df.columns = ['Profile Code', 'Length', 'Quantity']

# Create a sample Excel file in memory
sample_output = io.BytesIO()
sample_df.to_excel(sample_output, index=False)
sample_output.seek(0)

st.download_button(
    label="Tải Xuống Mẫu Biểu Mẫu",
    data=sample_output,
    file_name="mau_du_lieu_nhap.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# Footer
st.markdown("---")
st.markdown("Phần Mềm Tối Ưu Cắt Nhôm © 2025 By Cuong Vu")
