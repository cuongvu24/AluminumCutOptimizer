import pandas as pd
import streamlit as st
import io
import openpyxl
from openpyxl.styles import PatternFill

def validate_input_excel(df):
    required_columns = ["Mã Thanh", "Chiều Dài", "Số Lượng"]

    # Kiểm tra các cột bắt buộc
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        return False, f"Thiếu các cột bắt buộc: {', '.join(missing)}"

    # Kiểm tra dữ liệu
    try:
        df['Chiều Dài'] = pd.to_numeric(df['Chiều Dài'])
        df['Số Lượng'] = pd.to_numeric(df['Số Lượng'])
    except ValueError:
        return False, "Chiều Dài và Số Lượng phải là số"

    if (df['Chiều Dài'] <= 0).any():
        return False, "Chiều Dài phải > 0"
    if (df['Số Lượng'] <= 0).any():
        return False, "Số Lượng phải > 0"
    if df['Mã Thanh'].isnull().any() or (df['Mã Thanh'] == '').any():
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

    # Xuất ra file Excel
    with pd.ExcelWriter(output_stream, engine='openpyxl') as writer:
        grouped.to_excel(writer, sheet_name="Tổng Hợp Phụ Kiện", index=False)

    return grouped

def create_output_excel(output_stream, result_df, patterns_df, summary_df, stock_length_options, cutting_gap):
    with pd.ExcelWriter(output_stream, engine='openpyxl') as writer:
        # Ghi các sheet hiện có
        summary_df.to_excel(writer, sheet_name="Tổng Hợp", index=False)
        patterns_df.to_excel(writer, sheet_name="Mẫu Cắt", index=False)
        result_df.to_excel(writer, sheet_name="Chi Tiết Mảnh", index=False)

        # Tạo sheet "Mô Phỏng Cắt Từng Thanh"
        try:
            ws = writer.book.create_sheet("Mô Phỏng Cắt Từng Thanh")

            # Kiểm tra nếu patterns_df không rỗng
            if not patterns_df.empty:
                # Sắp xếp patterns_df theo cột 'Mã Thanh'
                patterns_df = patterns_df.sort_values('Mã Thanh')

                # Xác định số đoạn cắt tối đa trong bất kỳ mẫu cắt nào
                if 'Mẫu Cắt' in patterns_df.columns:
                    max_pieces = patterns_df['Mẫu Cắt'].apply(lambda x: len(x.split('+'))).max()
                else:
                    max_pieces = 0

                # Danh sách màu HEX cho các đoạn cắt
                piece_colors = ["FF9999", "99FF99", "9999FF", "FFFF99", "FF99FF", "99FFFF"]

                # Các cột gốc (loại bỏ 'Mẫu Cắt' nếu có)
                original_columns = [col for col in patterns_df.columns if col != 'Mẫu Cắt']

                # Các cột cho từng đoạn cắt
                piece_columns = [f"Piece {i+1}" for i in range(max_pieces)] if max_pieces > 0 else []

                # Ghi tiêu đề cho sheet "Mô Phỏng Cắt Từng Thanh"
                headers = original_columns + piece_columns
                for col_num, header in enumerate(headers, 1):
                    ws.cell(row=1, column=col_num, value=header)

                # Chỉ số cột trong patterns_df
                column_indices = {col: i for i, col in enumerate(patterns_df.columns)}

                # Ghi dữ liệu vào sheet
                for row_num, row in enumerate(patterns_df.itertuples(index=False), 2):
                    # Ghi các cột gốc
                    for col_num, col in enumerate(original_columns, 1):
                        value = row[column_indices[col]]
                        if isinstance(value, float):
                            # Nếu là số thập phân, làm tròn đến 1 chữ số thập phân
                            if value % 1 != 0:  # Kiểm tra nếu không phải số nguyên
                                value = round(value, 1)
                                ws.cell(row=row_num, column=col_num, value=value).number_format = '0.0'
                            else:
                                # Nếu là số nguyên, giữ nguyên
                                ws.cell(row=row_num, column=col_num, value=int(value)).number_format = '0'
                        else:
                            ws.cell(row=row_num, column=col_num, value=value)

                    # Tách mẫu cắt và ghi từng đoạn nếu có cột Mẫu Cắt
                    if 'Mẫu Cắt' in patterns_df.columns:
                        pieces = row[column_indices['Mẫu Cắt']].split('+')
                        for piece_num, piece in enumerate(pieces):
                            col_num = len(original_columns) + piece_num + 1
                            value = float(piece)
                            # Nếu là số thập phân, làm tròn đến 1 chữ số thập phân
                            if value % 1 != 0:  # Kiểm tra nếu không phải số nguyên
                                value = round(value, 1)
                                cell = ws.cell(row=row_num, column=col_num, value=value)
                                cell.number_format = '0.0'
                            else:
                                # Nếu là số nguyên, giữ nguyên
                                cell = ws.cell(row=row_num, column=col_num, value=int(value))
                                cell.number_format = '0'
                            # Áp dụng màu nền
                            color = piece_colors[piece_num % len(piece_colors)]
                            fill = PatternFill(start_color=color, end_color=color, fill_type="solid")
                            cell.fill = fill
            else:
                # Nếu patterns_df rỗng, ghi một thông báo vào sheet
                ws.cell(row=1, column=1, value="Không có dữ liệu để mô phỏng cắt.")
        except Exception as e:
            # Nếu có lỗi, ghi thông báo lỗi vào sheet
            ws = writer.book.create_sheet("Mô Phỏng Cắt Từng Thanh")
            ws.cell(row=1, column=1, value=f"Lỗi khi tạo sheet: {str(e)}")

        # Sheet Tham Số
        params_df = pd.DataFrame({
            'Tham Số': ['Kích Thước Thanh Có Sẵn', 'Khoảng Cách Cắt'],
            'Giá Trị': [', '.join(map(str, stock_length_options)), cutting_gap]
        })
        params_df.to_excel(writer, sheet_name="Tham Số", index=False)
