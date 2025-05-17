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

    # Chuyển đổi tên cột tiếng Việt sang tiếng Anh nếu có
    for vn_col, en_col in vietnamese_columns.items():
        if vn_col in df.columns:
            df.rename(columns={vn_col: en_col}, inplace=True)

    # Kiểm tra các cột bắt buộc
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        return False, f"Thiếu các cột bắt buộc: {', '.join(missing)}"

    # Kiểm tra dữ liệu số
    try:
        df['Length'] = pd.to_numeric(df['Length'])
        df['Quantity'] = pd.to_numeric(df['Quantity'])
    except ValueError:
        return False, "Chiều Dài và Số Lượng phải là số"

    # Kiểm tra giá trị hợp lệ
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
    required_cols = ['Mã phụ kiện', 'Tên phụ phiện', 'Đơn vị tính', 'Số lượng']
    missing = [col for col in required_cols if col not in input_df.columns]
    if missing:
        raise ValueError(f"Thiếu cột: {', '.join(missing)}")

    # Nhóm và tính tổng số lượng
    grouped = input_df.groupby(['Mã phụ kiện', 'Tên phụ phiện', 'Đơn vị tính'])['Số lượng'].sum().reset_index()
    grouped = grouped.rename(columns={'Số lượng': 'Tổng Số Lượng'})

    # Ghi vào file Excel
    with pd.ExcelWriter(output_stream, engine='openpyxl') as writer:
        grouped.to_excel(writer, sheet_name="Tổng Hợp Phụ Kiện", index=False)

    return grouped

def create_output_excel(output_stream, result_df, patterns_df, summary_df, stock_length_options, cutting_gap):
    with pd.ExcelWriter(output_stream, engine='openpyxl') as writer:
        summary_df.to_excel(writer, sheet_name="Tổng Hợp", index=False)
        patterns_df.to_excel(writer, sheet_name="Mẫu Cắt", index=False)
        result_df.to_excel(writer, sheet_name="Chi Tiết Mảnh", index=False)

        # Ghi thông tin tham số
        params_df = pd.DataFrame({
            'Tham Số': ['Kích Thước Thanh Có Sẵn', 'Khoảng Cách Cắt'],
            'Giá Trị': [', '.join(map(str, stock_length_options)), cutting_gap]
        })
        params_df.to_excel(writer, sheet_name="Tham Số", index=False)
