import pandas as pd
import numpy as np


def validate_input_excel(df):
    """
    Validates that the input Excel file has the required structure.
    
    Args:
        df (DataFrame): The input DataFrame to validate
        
    Returns:
        tuple: (is_valid, message) - Whether the file is valid and an error message if not
    """
    required_columns = ["Profile Code", "Length", "Quantity"]
    vietnamese_columns = {
        "Mã Thanh": "Profile Code",
        "Chiều Dài": "Length", 
        "Số Lượng": "Quantity"
    }
    
    # Map Vietnamese column names to English if present
    for vn_col, en_col in vietnamese_columns.items():
        if vn_col in df.columns:
            df.rename(columns={vn_col: en_col}, inplace=True)
    
    # Check if required columns exist
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        return False, f"Thiếu các cột bắt buộc: {', '.join(missing_columns)}"
    
    # Check if data types are correct
    try:
        df['Length'] = pd.to_numeric(df['Length'])
        df['Quantity'] = pd.to_numeric(df['Quantity'])
    except ValueError:
        return False, "Các cột 'Chiều Dài' và 'Số Lượng' phải chứa giá trị số"
    
    # Check if there are any negative or zero values
    if (df['Length'] <= 0).any():
        return False, "Giá trị 'Chiều Dài' phải là số dương"
    
    if (df['Quantity'] <= 0).any():
        return False, "Giá trị 'Số Lượng' phải là số dương"
    
    # Check if there are any empty profile codes
    if df['Profile Code'].isnull().any() or (df['Profile Code'] == '').any():
        return False, "'Mã Thanh' không được để trống"
    
    # Check if there's actually data in the file
    if len(df) == 0:
        return False, "Tệp không chứa bất kỳ dữ liệu nào"
    
    return True, "Tệp hợp lệ"


def create_output_excel(output_stream, result_df, patterns_df, summary_df, stock_length, cutting_gap):
    """
    Creates an Excel file with the optimization results.
    
    Args:
        output_stream: The BytesIO stream to write the Excel file to
        result_df (DataFrame): DataFrame with individual piece assignments
        patterns_df (DataFrame): DataFrame with cutting patterns
        summary_df (DataFrame): DataFrame with optimization summary
        stock_length (float): Standard stock length used for optimization
        cutting_gap (float): Cutting gap used for optimization
    """
    # Create copies with Vietnamese headers for the Excel output
    summary_vi = summary_df.copy()
    summary_vi.columns = [
        'Mã Thanh', 
        'Tổng Số Thanh', 
        'Tổng Thanh Sử Dụng', 
        'Tổng Chiều Dài Cần (mm)', 
        'Tổng Chiều Dài Nguyên Liệu (mm)', 
        'Phế Liệu (mm)', 
        'Hiệu Suất Tổng Thể', 
        'Hiệu Suất Trung Bình'
    ]
    summary_vi['Hiệu Suất Tổng Thể'] = summary_vi['Hiệu Suất Tổng Thể'].apply(lambda x: x)
    summary_vi['Hiệu Suất Trung Bình'] = summary_vi['Hiệu Suất Trung Bình'].apply(lambda x: x)
    
    patterns_vi = patterns_df.copy()
    patterns_vi.columns = [
        'Mã Thanh', 
        'Số Thanh', 
        'Chiều Dài Tiêu Chuẩn', 
        'Chiều Dài Sử Dụng', 
        'Chiều Dài Còn Lại', 
        'Hiệu Suất', 
        'Mẫu Cắt', 
        'Số Mảnh'
    ]
    
    result_vi = result_df.copy()
    result_vi.columns = [
        'Mã Thanh',
        'Mã Mảnh',
        'Chiều Dài',
        'Số Thanh'
    ]
    
    # Create Excel writer object
    with pd.ExcelWriter(output_stream, engine='openpyxl') as writer:
        # Add a summary sheet
        summary_vi.to_excel(writer, sheet_name='Tổng Hợp', index=False)
        
        # Add a cutting patterns sheet
        patterns_vi.to_excel(writer, sheet_name='Mẫu Cắt', index=False)
        
        # Add a piece assignments sheet
        result_vi.to_excel(writer, sheet_name='Chi Tiết Mảnh', index=False)
        
        # Add a parameters sheet
        params_df = pd.DataFrame({
            'Tham Số': ['Chiều Dài Tiêu Chuẩn', 'Khoảng Cách Cắt'],
            'Giá Trị': [stock_length, cutting_gap]
        })
        params_df.to_excel(writer, sheet_name='Tham Số', index=False)

        # Format the sheets
        workbook = writer.book
        
        # Format Summary sheet
        worksheet = writer.sheets['Tổng Hợp']
        worksheet.column_dimensions['A'].width = 15
        worksheet.column_dimensions['B'].width = 15
        worksheet.column_dimensions['C'].width = 15
        worksheet.column_dimensions['D'].width = 22
        worksheet.column_dimensions['E'].width = 22
        worksheet.column_dimensions['F'].width = 15
        worksheet.column_dimensions['G'].width = 20
        worksheet.column_dimensions['H'].width = 20
        
        # Format Cutting Patterns sheet
        worksheet = writer.sheets['Mẫu Cắt']
        worksheet.column_dimensions['A'].width = 15
        worksheet.column_dimensions['B'].width = 15
        worksheet.column_dimensions['C'].width = 18
        worksheet.column_dimensions['D'].width = 18
        worksheet.column_dimensions['E'].width = 18
        worksheet.column_dimensions['F'].width = 15
        worksheet.column_dimensions['G'].width = 40
        worksheet.column_dimensions['H'].width = 15
        
        # Format Piece Assignments sheet
        worksheet = writer.sheets['Chi Tiết Mảnh']
        worksheet.column_dimensions['A'].width = 15
        worksheet.column_dimensions['B'].width = 30
        worksheet.column_dimensions['C'].width = 15
        worksheet.column_dimensions['D'].width = 15
