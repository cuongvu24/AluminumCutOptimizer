import pandas as pd
import streamlit as st
import io
import openpyxl
from openpyxl.styles import PatternFill

def validate_input_excel(df):
    required_columns = ["Profile Code", "Length", "Quantity"]
    vietnamese_columns = {
        "Mã Thanh": "Profile Code",
        "Chiều Dài": "Length",
        "Số Lượng": "Quantity"
    }

    # Đổi tên cột từ tiếng Việt sang tiếng Anh nếu cần
    for vn_col, en_col in vietnamese_columns.items():
        if vn_col in df.columns:
            df.rename(columns={vn_col: en_col}, inplace=True)

    # Kiểm tra các cột bắt buộc
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        return False, f"Thiếu các cột bắt buộc: {', '.join(missing)}"

    # Kiểm tra dữ liệu
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

def optimize_cutting(df, cutting_gap, optimization_method, stock_length_options, optimize_stock_length):
    """
    Hàm tối ưu hóa cắt nhôm (triển khai thực tế).
    
    Tham số:
    - df: DataFrame chứa dữ liệu đầu vào (Profile Code, Length, Quantity)
    - cutting_gap: Khoảng cách cắt (mm)
    - optimization_method: Phương pháp tối ưu ("Tối Ưu Hiệu Suất Cao Nhất" hoặc "Tối Ưu Số Lượng Thanh")
    - stock_length_options: Danh sách kích thước thanh có sẵn (mm)
    - optimize_stock_length: Có tối ưu hóa kích thước thanh hay không
    
    Trả về:
    - result_df: DataFrame chi tiết mảnh cắt
    - patterns_df: DataFrame mẫu cắt
    - summary_df: DataFrame tổng hợp
    """
    # Kiểm tra danh sách kích thước thanh
    if stock_length_options is None or not stock_length_options:
        raise ValueError("Vui lòng cung cấp ít nhất một kích thước thanh.")

    # Mở rộng dữ liệu theo số lượng
    expanded_data = []
    for idx, row in df.iterrows():
        for i in range(int(row['Quantity'])):
            expanded_data.append({
                'Profile Code': row['Profile Code'],
                'Length': row['Length'],
                'Item ID': f"{row['Profile Code']}_{i+1}"
            })
    expanded_df = pd.DataFrame(expanded_data)

    profile_codes = expanded_df['Profile Code'].unique()
    all_patterns = []
    all_summaries = []
    all_results = []

    for profile_code in profile_codes:
        profile_data = expanded_df[expanded_df['Profile Code'] == profile_code].copy()
        lengths = profile_data['Length'].values
        lengths = sorted(lengths, reverse=True)  # Sắp xếp giảm dần

        best_patterns = []
        best_remaining_lengths = []
        best_stock_length = stock_length_options[0]
        best_efficiency = 0
        best_bar_count = float('inf')

        # Thử từng kích thước thanh có sẵn
        for current_stock_length in stock_length_options:
            patterns = []
            remaining_lengths = []

            for length in lengths:
                added = False
                for i, remaining in enumerate(remaining_lengths):
                    if length <= remaining - cutting_gap:
                        patterns[i].append(length)
                        remaining_lengths[i] -= (length + cutting_gap)
                        added = True
                        break
                if not added:
                    patterns.append([length])
                    remaining_lengths.append(current_stock_length - length - cutting_gap)

            total_used_length = sum(sum(pattern) for pattern in patterns)
            total_stock_length = current_stock_length * len(patterns)
            current_efficiency = total_used_length / total_stock_length if total_stock_length > 0 else 0

            if optimization_method == "Tối Ưu Hiệu Suất Cao Nhất":
                if current_efficiency > best_efficiency:
                    best_patterns = patterns
                    best_remaining_lengths = remaining_lengths
                    best_stock_length = current_stock_length
                    best_efficiency = current_efficiency
                    best_bar_count = len(patterns)
            else:  # Tối Ưu Số Lượng Thanh
                if len(patterns) < best_bar_count or (len(patterns) == best_bar_count and current_efficiency > best_efficiency):
                    best_patterns = patterns
                    best_remaining_lengths = remaining_lengths
                    best_stock_length = current_stock_length
                    best_efficiency = current_efficiency
                    best_bar_count = len(patterns)

        patterns = best_patterns
        remaining_lengths = best_remaining_lengths
        current_stock_length = best_stock_length

        # Tạo dữ liệu mẫu cắt
        pattern_data = []
        bar_number = 1

        for pattern, remaining in zip(patterns, remaining_lengths):
            used_length = sum(pattern)
            efficiency = used_length / current_stock_length if current_stock_length > 0 else 0
            pattern_data.append({
                'Profile Code': profile_code,
                'Bar Number': bar_number,
                'Stock Length': current_stock_length,
                'Used Length': used_length,
                'Remaining Length': remaining,
                'Efficiency': efficiency,
                'Cutting Pattern': '+'.join(map(str, pattern)),
                'Pieces': len(pattern)
            })

            # Gán mảnh cắt vào thanh
            for length in pattern:
                unassigned_items = profile_data[(profile_data['Length'] == length) &
                                               (~profile_data['Item ID'].isin([r.get('Item ID') for r in all_results]))]
                if not unassigned_items.empty:
                    item_idx = unassigned_items.index[0]
                    all_results.append({
                        'Profile Code': profile_code,
                        'Item ID': profile_data.loc[item_idx, 'Item ID'],
                        'Length': length,
                        'Bar Number': bar_number
                    })
                    profile_data = profile_data.drop(item_idx)

            bar_number += 1

        all_patterns.extend(pattern_data)

        # Tạo dữ liệu tổng hợp
        total_bars = len(patterns)
        total_length_needed = sum(lengths)
        total_length_used = sum(pattern['Stock Length'] for pattern in pattern_data)
        avg_efficiency = sum(p['Efficiency'] for p in pattern_data) / len(pattern_data) if pattern_data else 0

        all_summaries.append({
            'Profile Code': profile_code,
            'Total Pieces': len(lengths),
            'Total Bars Used': total_bars,
            'Total Length Needed (mm)': total_length_needed,
            'Total Stock Length (mm)': total_length_used,
            'Waste (mm)': total_length_used - total_length_needed - (len(lengths) - total_bars) * cutting_gap,
            'Overall Efficiency': total_length_needed / total_length_used if total_length_used > 0 else 0,
            'Average Bar Efficiency': avg_efficiency
        })

    # Tạo DataFrame kết quả
    patterns_df = pd.DataFrame(all_patterns)
    summary_df = pd.DataFrame(all_summaries)
    result_df = pd.DataFrame(all_results)

    # Sắp xếp và định dạng
    if not patterns_df.empty:
        patterns_df = patterns_df.sort_values(['Profile Code', 'Bar Number']).reset_index(drop=True)
        patterns_df['Efficiency'] = patterns_df['Efficiency'].round(4)

    if not summary_df.empty:
        summary_df = summary_df.sort_values('Profile Code').reset_index(drop=True)
        summary_df['Overall Efficiency'] = summary_df['Overall Efficiency'].round(4)
        summary_df['Average Bar Efficiency'] = summary_df['Average Bar Efficiency'].round(4)

    if not result_df.empty:
        result_df = result_df.sort_values(['Profile Code', 'Bar Number']).reset_index(drop=True)

    return result_df, patterns_df, summary_df

def create_output_excel(output_stream, result_df, patterns_df, summary_df, stock_length_options, cutting_gap):
    with pd.ExcelWriter(output_stream, engine='openpyxl') as writer:
        # Ghi các sheet hiện có
        summary_df.to_excel(writer, sheet_name="Tổng Hợp", index=False)
        patterns_df.to_excel(writer, sheet_name="Mẫu Cắt", index=False)
        result_df.to_excel(writer, sheet_name="Chi Tiết Mảnh", index=False)

        # Tạo sheet mới: Mô Phỏng Cắt
        ws = writer.book.create_sheet("Mô Phỏng Cắt")

        # Sắp xếp patterns_df theo Profile Code để nhóm mã nhôm
        patterns_df = patterns_df.sort_values('Profile Code')

        # Xác định số đoạn cắt tối đa trong bất kỳ mẫu cắt nào
        max_pieces = patterns_df['Cutting Pattern'].apply(lambda x: len(x.split('+'))).max()

        # Danh sách màu HEX cho các đoạn cắt
        piece_colors = ["FF9999", "99FF99", "9999FF", "FFFF99", "FF99FF", "99FFFF"]

        # Các cột gốc (loại bỏ 'Cutting Pattern')
        original_columns = [col for col in patterns_df.columns if col != 'Cutting Pattern']

        # Các cột cho từng đoạn cắt
        piece_columns = [f"Piece {i+1}" for i in range(max_pieces)]

        # Ghi tiêu đề cho sheet "Mô Phỏng Cắt"
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
                ws.cell(row=row_num, column=col_num, value=value)

            # Tách mẫu cắt và ghi từng đoạn
            pieces = row[column_indices['Cutting Pattern']].split('+')
            for piece_num, piece in enumerate(pieces):
                col_num = len(original_columns) + piece_num + 1
                cell = ws.cell(row=row_num, column=col_num, value=float(piece))
                # Áp dụng màu nền
                color = piece_colors[piece_num % len(piece_colors)]
                fill = PatternFill(start_color=color, end_color=color, fill_type="solid")
                cell.fill = fill

        # Sheet Tham Số
        params_df = pd.DataFrame({
            'Tham Số': ['Kích Thước Thanh Có Sẵn', 'Khoảng Cách Cắt'],
            'Giá Trị': [', '.join(map(str, stock_length_options)), cutting_gap]
        })
        params_df.to_excel(writer, sheet_name="Tham Số", index=False)
