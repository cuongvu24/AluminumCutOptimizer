import pandas as pd
import streamlit as st
import io
import openpyxl
from openpyxl.styles import PatternFill
from pulp import LpMinimize, LpProblem, LpVariable, lpSum, PULP_CBC_CMD

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

def optimize_with_pulp(profile_data, cutting_gap, stock_length_options):
    """Tối ưu hóa cắt nhôm bằng PuLP với giới hạn số mẫu cắt và số đoạn cắt tối đa."""
    lengths = profile_data['Chiều Dài'].values
    quantities = [1] * len(lengths)  # Mỗi mục đã được mở rộng theo số lượng
    item_ids = profile_data['Item ID'].values
    profile_code = profile_data['Mã Thanh'].iloc[0]
    has_door_code = "Mã Cửa" in profile_data.columns
    max_patterns = 10000  # Tăng giới hạn mẫu cắt
    max_cuts_per_pattern = 10  # Giới hạn số đoạn cắt tối đa trong mỗi mẫu

    # Kiểm tra dữ liệu đầu vào
    total_items = len(lengths)
    if total_items > 100:
        st.warning(f"Dữ liệu cho {profile_code} có {total_items} mục. Tối ưu hóa PuLP có thể chậm hoặc bỏ sót mẫu. Xem xét dùng phương pháp 'Tối Ưu Linh Hoạt'.")

    # Tạo danh sách mẫu cắt khả thi
    patterns = []
    pattern_count = 0

    for stock_length in stock_length_options:
        def generate_patterns(current_pattern, remaining_length, index):
            nonlocal pattern_count
            if pattern_count >= max_patterns or len(current_pattern) >= max_cuts_per_pattern:
                return
            if index >= len(lengths):
                if current_pattern:
                    patterns.append((current_pattern[:], stock_length))
                    pattern_count += 1
                return
            length = lengths[index]
            if length <= remaining_length - cutting_gap:
                current_pattern.append(index)
                generate_patterns(current_pattern, remaining_length - length - cutting_gap, index + 1)
                current_pattern.pop()
            generate_patterns(current_pattern, remaining_length, index + 1)

        generate_patterns([], stock_length, 0)
        if pattern_count >= max_patterns:
            st.warning(f"Đạt giới hạn {max_patterns} mẫu cắt cho {profile_code}. Một số mẫu có thể bị bỏ sót. Xem xét giảm số lượng dữ liệu hoặc dùng phương pháp khác.")
            break

    # Kiểm tra nếu không có mẫu cắt nào được tạo
    if not patterns:
        st.error(f"Không tạo được mẫu cắt nào cho {profile_code}. Vui lòng kiểm tra dữ liệu hoặc tăng max_patterns.")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    # Tạo mô hình PuLP
    prob = LpProblem(f"Cutting_Stock_{profile_code}", LpMinimize)
    
    # Biến quyết định: số lần sử dụng mỗi mẫu cắt
    pattern_vars = LpVariable.dicts("Pattern", range(len(patterns)), lowBound=0, cat='Integer')
    
    # Hàm mục tiêu: tối thiểu hóa số thanh sử dụng
    prob += lpSum(pattern_vars[i] for i in range(len(patterns)))
    
    # Ràng buộc: đáp ứng số lượng yêu cầu cho mỗi chiều dài
    for j in range(len(lengths)):
        prob += lpSum(
            sum(1 for idx in patterns[i][0] if idx == j) * pattern_vars[i]
            for i in range(len(patterns))
        ) >= quantities[j], f"Demand_{j}"
    
    # Giải bài toán
    prob.solve(PULP_CBC_CMD(msg=False, timeLimit=30))  # Giới hạn thời gian giải 30 giây
    
    # Xử lý kết quả
    patterns_data = []
    results = []
    bar_number = 1
    stock_lengths_used = []
    remaining_lengths = []
    
    for i in range(len(patterns)):
        if pattern_vars[i].varValue and pattern_vars[i].varValue > 0:
            pattern_indices, stock_length = patterns[i]
            used_length = sum(lengths[idx] for idx in pattern_indices)
            remaining = stock_length - used_length - (len(pattern_indices) - 1) * cutting_gap
            efficiency = used_length / stock_length if stock_length > 0 else 0
            
            pattern_rounded = [round(lengths[idx], 1) if lengths[idx] % 1 != 0 else int(lengths[idx]) for idx in pattern_indices]
            patterns_data.append({
                'Mã Thanh': profile_code,
                'Số Thanh': bar_number,
                'Chiều Dài Thanh': stock_length,
                'Chiều Dài Sử Dụng': used_length,
                'Chiều Dài Còn Lại': remaining,
                'Hiệu Suất': efficiency,
                'Mẫu Cắt': '+'.join(map(str, pattern_rounded)),
                'Số Đoạn Cắt': len(pattern_indices)
            })
            stock_lengths_used.append(stock_length)
            remaining_lengths.append(remaining)
            
            # Gán mảnh cắt
            for idx in pattern_indices:
                result_item = {
                    'Mã Thanh': profile_code,
                    'Item ID': item_ids[idx],
                    'Chiều Dài': lengths[idx],
                    'Số Thanh': bar_number
                }
                if has_door_code:
                    result_item['Mã Cửa'] = profile_data.iloc[idx]['Mã Cửa']
                results.append(result_item)
            
            bar_number += 1
    
    patterns_df = pd.DataFrame(patterns_data)
    result_df = pd.DataFrame(results)
    
    # Tạo summary_df
    total_bars = len(patterns_data)
    total_length_needed = sum(lengths)
    total_length_used = sum(p['Chiều Dài Thanh'] for p in patterns_data)
    avg_efficiency = sum(p['Hiệu Suất'] for p in patterns_data) / len(patterns_data) if patterns_data else 0
    overall_efficiency = (total_length_needed / total_length_used if total_length_used > 0 else 0) * 100
    waste = total_length_used - total_length_needed - (len(lengths) - total_bars) * cutting_gap

    summary_df = pd.DataFrame([{
        'Mã Thanh': profile_code,
        'Tổng Đoạn Cắt': len(lengths),
        'Số Thanh Sử Dụng': total_bars,
        'Tổng Chiều Dài Cần (mm)': total_length_needed,
        'Tổng Chiều Dài Nguyên Liệu (mm)': total_length_used,
        'Phế Liệu (mm)': waste,
        'Hiệu Suất Tổng Thể': overall_efficiency,
        'Hiệu Suất Trung Bình': avg_efficiency
    }])
    
    return result_df, patterns_df, summary_df

def optimize_cutting(df, cutting_gap, optimization_method, stock_length_options, optimize_stock_length):
    """
    Hàm tối ưu hóa cắt nhôm, hỗ trợ bốn chế độ tối ưu:
    - "Tối Ưu Hiệu Suất Cao Nhất": Chọn một kích thước thanh tốt nhất cho từng mã nhôm để tối ưu hiệu suất.
    - "Tối Ưu Số Lượng Thanh": Chọn một kích thước thanh tốt nhất để giảm số lượng thanh.
    - "Tối Ưu Linh Hoạt": Sử dụng nhiều kích thước thanh để giảm phế liệu.
    - "Tối Ưu PuLP": Sử dụng lập trình tuyến tính với PuLP để tối ưu chính xác.
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

        if optimization_method == "Tối Ưu PuLP":
            # Sử dụng PuLP để tối ưu
            result_df, patterns_df, summary_df = optimize_with_pulp(profile_data, cutting_gap, stock_length_options)
            if not result_df.empty:
                all_results.extend(result_df.to_dict('records'))
                all_patterns.extend(patterns_df.to_dict('records'))
                all_summaries.extend(summary_df.to_dict('records'))
            continue

        patterns = []
        remaining_lengths = []
        stock_lengths_used = []

        if optimization_method == "Tối Ưu Linh Hoạt":
            # Chế độ linh hoạt: Sử dụng nhiều kích thước thanh
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

                # Thử tạo thanh mới
                for stock_length in stock_length_options:
                    temp_remaining = stock_length - length - cutting_gap
                    if temp_remaining >= 0 and temp_remaining < best_remaining:
                        best_remaining = temp_remaining
                        best_fit = [length]
                        best_stock_length = stock_length
                        best_pattern_idx = -1

                if best_pattern_idx >= 0:
                    patterns[best_pattern_idx].append(length)
                    remaining_lengths[best_pattern_idx] = best_remaining
                else:
                    patterns.append(best_fit)
                    remaining_lengths.append(best_remaining)
                    stock_lengths_used.append(best_stock_length)
        else:
            # Chế độ cũ: Chọn một kích thước thanh tốt nhất
            best_patterns = []
            best_remaining_lengths = []
            best_stock_length = stock_length_options[0]
            best_efficiency = 0
            best_bar_count = float('inf')

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
            stock_lengths_used = [best_stock_length] * len(patterns)

        # Tạo dữ liệu mẫu cắt
        pattern_data = []
        bar_number = 1
        for pattern, remaining, stock_length in zip(patterns, remaining_lengths, stock_lengths_used):
            used_length = sum(pattern)
            efficiency = used_length / stock_length if stock_length > 0 else 0
            efficiency = max(0, min(100, efficiency * 100))
            pattern_rounded = [round(x, 1) if x % 1 != 0 else int(x) for x in pattern]
            pattern_data.append({
                'Mã Thanh': profile_code,
                'Số Thanh': bar_number,
                'Chiều Dài Thanh': stock_length,
                'Chiều Dài Sử Dụng': used_length,
                'Chiều Dài Còn Lại': remaining,
                'Hiệu Suất': efficiency,
                'Mẫu Cắt': '+'.join(map(str, pattern_rounded)),
                'Số Đoạn Cắt': len(pattern)
            })

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
                    if has_door_code:
                        result_item['Mã Cửa'] = profile_data.loc[item_idx, 'Mã Cửa']
                    all_results.append(result_item)
                    profile_data = profile_data.drop(item_idx)

            bar_number += 1

        all_patterns.extend(pattern_data)

        total_bars = len(patterns)
        total_length_needed = sum(lengths)
        total_length_used = sum(pattern['Chiều Dài Thanh'] for pattern in pattern_data)
        avg_efficiency = sum(p['Hiệu Suất'] for p in pattern_data) / len(pattern_data) if pattern_data else 0
        overall_efficiency = (total_length_needed / total_length_used if total_length_used > 0 else 0) * 100
        overall_efficiency = max(0, min(100, overall_efficiency))
        avg_efficiency = max(0, min(100, avg_efficiency))
        waste = total_length_used - total_length_needed - (len(lengths) - total_bars) * cutting_gap

        all_summaries.append({
            'Mã Thanh': profile_code,
            'Tổng Đoạn Cắt': len(lengths),
            'Số Thanh Sử Dụng': total_bars,
            'Tổng Chiều Dài Cần (mm)': total_length_needed,
            'Tổng Chiều Dài Nguyên Liệu (mm)': total_length_used,
            'Phế Liệu (mm)': waste,
            'Hiệu Suất Tổng Thể': overall_efficiency,
            'Hiệu Suất Trung Bình': avg_efficiency
        })

    patterns_df = pd.DataFrame(all_patterns)
    summary_df = pd.DataFrame(all_summaries)
    result_df = pd.DataFrame(all_results)

    if not patterns_df.empty:
        patterns_df = patterns_df.sort_values(['Mã Thanh', 'Số Thanh']).reset_index(drop=True)
        patterns_df['Chiều Dài Sử Dụng'] = patterns_df['Chiều Dài Sử Dụng'].apply(lambda x: round(x, 1) if x % 1 != 0 else int(x))
        patterns_df['Chiều Dài Còn Lại'] = patterns_df['Chiều Dài Còn Lại'].apply(lambda x: round(x, 1) if x % 1 != 0 else int(x))

    if not summary_df.empty:
        summary_df = summary_df.sort_values('Mã Thanh').reset_index(drop=True)
        summary_df['Phế Liệu (mm)'] = summary_df['Phế Liệu (mm)'].apply(lambda x: round(x, 1) if x % 1 != 0 else int(x))

    if not result_df.empty:
        result_df = result_df.sort_values(['Mã Thanh', 'Số Thanh']).reset_index(drop=True)

    return result_df, patterns_df, summary_df
