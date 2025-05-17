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

def optimize_cutting(df, cutting_gap, optimization_method, stock_length_options, optimize_stock_length):
    """
    Hàm tối ưu hóa cắt nhôm, hỗ trợ ba chế độ tối ưu:
    - "Tối Ưu Hiệu Suất Cao Nhất": Chọn một kích thước thanh tốt nhất cho từng mã nhôm để tối ưu hiệu suất.
    - "Tối Ưu Số Lượng Thanh": Chọn một kích thước thanh tốt nhất cho từng mã nhôm để tối ưu số lượng thanh.
    - "Tối Ưu Linh Hoạt": Sử dụng nhiều kích thước thanh để giảm phế liệu cho từng mã nhôm.
    
    Tham số:
    - df: DataFrame chứa dữ liệu đầu vào (Mã Thanh, Chiều Dài, Số Lượng, [Mã Cửa])
    - cutting_gap: Khoảng cách cắt (mm)
    - optimization_method: Phương pháp tối ưu ("Tối Ưu Hiệu Suất Cao Nhất", "Tối Ưu Số Lượng Thanh", "Tối Ưu Linh Hoạt")
    - stock_length_options: Danh sách kích thước thanh có sẵn (mm)
    - optimize_stock_length: Có tối ưu hóa kích thước thanh hay không (không sử dụng trong phiên bản này)
    
    Trả về:
    - result_df: DataFrame chi tiết mảnh cắt (bao gồm cột Mã Cửa)
    - patterns_df: DataFrame mẫu cắt
    - summary_df: DataFrame tổng hợp
    """
    # Kiểm tra danh sách kích thước thanh
    if stock_length_options is None or not stock_length_options:
        raise ValueError("Vui lòng cung cấp ít nhất một kích thước thanh.")

    # Kiểm tra xem cột "Mã Cửa" có tồn tại trong df không
    has_door_code = "Mã Cửa" in df.columns

    # Mở rộng dữ liệu theo số lượng
    expanded_data = []
    for idx, row in df.iterrows():
        for i in range(int(row['Số Lượng'])):
            item = {
                'Mã Thanh': row['Mã Thanh'],
                'Chiều Dài': row['Chiều Dài'],
                'Item ID': f"{row['Mã Thanh']}_{i+1}"
            }
            # Thêm cột "Mã Cửa" nếu có
            if has_door_code:
                item['Mã Cửa'] = row['Mã Cửa']
            expanded_data.append(item)
    expanded_df = pd.DataFrame(expanded_data)

    profile_codes = expanded_df['Mã Thanh'].unique()
    all_patterns = []
    all_summaries = []
    all_results = []

    for profile_code in profile_codes:
        profile_data = expanded_df[expanded_df['Mã Thanh'] == profile_code].copy()
        lengths = profile_data['Chiều Dài'].values
        lengths = sorted(lengths, reverse=True)  # Sắp xếp giảm dần để tối ưu

        patterns = []
        remaining_lengths = []
        stock_lengths_used = []  # Lưu kích thước thanh được sử dụng cho từng thanh

        if optimization_method == "Tối Ưu Linh Hoạt":
            # Chế độ linh hoạt: Sử dụng nhiều kích thước thanh cho mỗi mã nhôm
            for length in lengths:
                best_fit = None
                best_remaining = float('inf')
                best_pattern_idx = -1
                best_stock_length = None

                # Thử gán vào các thanh hiện có
                for i, (pattern, remaining) in enumerate(zip(patterns, remaining_lengths)):
                    if length <= remaining - cutting_gap:
                        temp_remaining = remaining - (length + cutting_gap)
                        if temp_remaining < best_remaining:
                            best_remaining = temp_remaining
                            best_pattern_idx = i

                # Thử tạo thanh mới với tất cả kích thước thanh
                for stock_length in stock_length_options:
                    temp_remaining = stock_length - length - cutting_gap
                    if temp_remaining >= 0 and temp_remaining < best_remaining:
                        best_remaining = temp_remaining
                        best_fit = [length]
                        best_stock_length = stock_length
                        best_pattern_idx = -1  # Đánh dấu để tạo thanh mới

                # Gán mảnh cắt vào thanh
                if best_pattern_idx >= 0:
                    # Gán vào thanh hiện có
                    patterns[best_pattern_idx].append(length)
                    remaining_lengths[best_pattern_idx] = best_remaining
                else:
                    # Tạo thanh mới
                    patterns.append(best_fit)
                    remaining_lengths.append(best_remaining)
                    stock_lengths_used.append(best_stock_length)
        else:
            # Chế độ cũ: Chọn một kích thước thanh tốt nhất cho mã nhôm hiện tại
            best_patterns = []
            best_remaining_lengths = []
            best_stock_length = stock_length_options[0]
            best_efficiency = 0
            best_bar_count = float('inf')

            # Thử từng kích thước thanh có sẵn
            for current_stock_length in stock_length_options:
                temp_patterns = []
                temp_remaining_lengths = []

                for length in lengths:
                    added = False
                    for i, remaining in enumerate(temp_remaining_lengths):
                        if length <= remaining - cutting_gap:
                            temp_patterns[i].append(length)
                            temp_remaining_lengths[i] -= (length + cutting_gap)
                            added = True
                            break
                    if not added:
                        temp_patterns.append([length])
                        temp_remaining_lengths.append(current_stock_length - length - cutting_gap)

                total_used_length = sum(sum(pattern) for pattern in temp_patterns)
                total_stock_length = current_stock_length * len(temp_patterns)
                current_efficiency = total_used_length / total_stock_length if total_stock_length > 0 else 0

                if optimization_method == "Tối Ưu Hiệu Suất Cao Nhất":
                    if current_efficiency > best_efficiency:
                        best_patterns = temp_patterns
                        best_remaining_lengths = temp_remaining_lengths
                        best_stock_length = current_stock_length
                        best_efficiency = current_efficiency
                        best_bar_count = len(temp_patterns)
                else:  # Tối Ưu Số Lượng Thanh
                    if len(temp_patterns) < best_bar_count or (len(temp_patterns) == best_bar_count and current_efficiency > best_efficiency):
                        best_patterns = temp_patterns
                        best_remaining_lengths = temp_remaining_lengths
                        best_stock_length = current_stock_length
                        best_efficiency = current_efficiency
                        best_bar_count = len(temp_patterns)

            patterns = best_patterns
            remaining_lengths = best_remaining_lengths
            # Với chế độ cũ, tất cả thanh của mã nhôm này sử dụng cùng một kích thước
            stock_lengths_used = [best_stock_length] * len(patterns)

        # Tạo dữ liệu mẫu cắt
        pattern_data = []
        bar_number = 1
        for pattern, remaining, stock_length in zip(patterns, remaining_lengths, stock_lengths_used):
            used_length = sum(pattern)
            efficiency = used_length / stock_length if stock_length > 0 else 0
            # Làm tròn các số trong pattern trước khi tạo chuỗi Cutting Pattern
            pattern_rounded = [round(x, 1) if x % 1 != 0 else int(x) for x in pattern]
            pattern_data.append({
                'Mã Thanh': profile_code,
                'Số Thanh': bar_number,
                'Chiều Dài Thanh': stock_length,
                'Chiều Dài Sử Dụng': used_length,
                'Chiều Dài Còn Lại': remaining,
                'Hiệu Suất': efficiency * 100,  # Chuyển đổi hiệu suất thành phần trăm
                'Mẫu Cắt': '+'.join(map(str, pattern_rounded)),
                'Số Đoạn Cắt': len(pattern)
            })

            # Gán mảnh cắt vào thanh
            for length in pattern:
                unassigned_items = profile_data[(profile_data['Chiều Dài'] == length) &
                                               (~profile_data['Item ID'].isin([r.get('Item ID') for r in all_results]))]
                if not unassigned_items.empty:
                    item_idx = unassigned_items.index[0]
                    result_item = {
                        'Mã Thanh': profile_code,
                        'Item ID': profile_data.loc[item_idx, 'Item ID'],
                        'Chiều Dài': length,
                        'Số Thanh': bar_number
                    }
                    # Thêm cột "Mã Cửa" nếu có
                    if has_door_code:
                        result_item['Mã Cửa'] = profile_data.loc[item_idx, 'Mã Cửa']
                    all_results.append(result_item)
                    profile_data = profile_data.drop(item_idx)

            bar_number += 1

        all_patterns.extend(pattern_data)

        # Tạo dữ liệu tổng hợp
        total_bars = len(patterns)
        total_length_needed = sum(lengths)
        total_length_used = sum(pattern['Chiều Dài Thanh'] for pattern in pattern_data)
        avg_efficiency = sum(p['Hiệu Suất'] for p in pattern_data) / len(pattern_data) if pattern_data else 0
        waste = total_length_used - total_length_needed - (len(lengths) - total_bars) * cutting_gap

        all_summaries.append({
            'Mã Thanh': profile_code,
            'Tổng Đoạn Cắt': len(lengths),
            'Số Thanh Sử Dụng': total_bars,
            'Tổng Chiều Dài Cần (mm)': total_length_needed,
            'Tổng Chiều Dài Nguyên Liệu (mm)': total_length_used,
            'Phế Liệu (mm)': waste,
            'Hiệu Suất Tổng Thể': (total_length_needed / total_length_used if total_length_used > 0 else 0) * 100,  # Chuyển đổi thành phần trăm
            'Hiệu Suất Trung Bình': avg_efficiency  # Đã nhân 100 ở pattern_data
        })

    # Tạo DataFrame kết quả
    patterns_df = pd.DataFrame(all_patterns)
    summary_df = pd.DataFrame(all_summaries)
    result_df = pd.DataFrame(all_results)

    # Sắp xếp và định dạng
    if not patterns_df.empty:
        patterns_df = patterns_df.sort_values(['Mã Thanh', 'Số Thanh']).reset_index(drop=True)
        # Định dạng số thập phân cho các cột khác
        patterns_df['Chiều Dài Sử Dụng'] = patterns_df['Chiều Dài Sử Dụng'].apply(lambda x: round(x, 1) if x % 1 != 0 else int(x))
        patterns_df['Chiều Dài Còn Lại'] = patterns_df['Chiều Dài Còn Lại'].apply(lambda x: round(x, 1) if x % 1 != 0 else int(x))

    if not summary_df.empty:
        summary_df = summary_df.sort_values('Mã Thanh').reset_index(drop=True)
        summary_df['Phế Liệu (mm)'] = summary_df['Phế Liệu (mm)'].apply(lambda x: round(x, 1) if x % 1 != 0 else int(x))

    if not result_df.empty:
        result_df = result_df.sort_values(['Mã Thanh', 'Số Thanh']).reset_index(drop=True)

    return result_df, patterns_df, summary_df
