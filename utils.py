import pandas as pd


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


def create_output_excel(output_stream, result_df, patterns_df, summary_df, stock_length, cutting_gap):
        summary_vi = summary_df.copy()
    patterns_vi = patterns_df.copy()
    result_vi = result_df.copy()

    # Ghi file Excel
    with pd.ExcelWriter(output_stream, engine='openpyxl') as writer:
        summary_vi.to_excel(writer, sheet_name='Tổng Hợp', index=False)
        patterns_vi.to_excel(writer, sheet_name='Mẫu Cắt', index=False)
        result_vi.to_excel(writer, sheet_name='Chi Tiết Mảnh', index=False)

        pd.DataFrame({
            'Tham Số': ['Chiều Dài Tiêu Chuẩn', 'Khoảng Cách Cắt'],
            'Giá Trị': [stock_length, cutting_gap]
        }).to_excel(writer, sheet_name='Tham Số', index=False)

        # Cài đặt chiều rộng cột sơ bộ
        for sheet in writer.sheets.values():
            for col in sheet.columns:
                sheet.column_dimensions[col[0].column_letter].width = 18
