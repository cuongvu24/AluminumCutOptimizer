import pandas as pd
import numpy as np

def optimize_cutting(input_data, stock_length, cutting_gap,
                     optimization_method="Tối Ưu Hiệu Suất Cao Nhất",
                     stock_length_options=None, optimize_stock_length=False):
    """
    Hàm tối ưu cắt nhôm:
    - Cho phép thử nhiều kích thước thanh.
    - Luôn ghép tối đa.
    - Ghi lại đoạn chưa ghép nếu còn sót.
    """

    if stock_length_options is None:
        stock_length_options = [stock_length]

    # Mở rộng dữ liệu
    expanded_data = []
    for _, row in input_data.iterrows():
        for i in range(int(row['Quantity'])):
            expanded_data.append({
                'Profile Code': row['Profile Code'],
                'Length': row['Length'],
                'Item ID': f"{row['Profile Code']}_{i+1}"
            })

    expanded_df = pd.DataFrame(expanded_data)

    # Kết quả
    all_patterns = []
    all_summaries = []
    all_results = []
    unassigned_total = []

    profile_codes = expanded_df['Profile Code'].unique()

    for profile_code in profile_codes:
        profile_data = expanded_df[expanded_df['Profile Code'] == profile_code].copy()
        lengths = profile_data['Length'].values
        lengths = np.sort(lengths)[::-1]

        best_patterns = []
        best_remaining_lengths = []
        best_stock_length = stock_length
        best_efficiency = 0
        best_bar_count = float('inf')

        for current_stock_length in stock_length_options:
            patterns = []
            remaining_lengths = []

            for length in lengths:
                added = False
                for i, remaining in enumerate(remaining_lengths):
                    if length + cutting_gap <= remaining:
                        patterns[i].append(length)
                        remaining_lengths[i] -= (length + cutting_gap)
                        added = True
                        break

                if not added:
                    if length + cutting_gap <= current_stock_length:
                        patterns.append([length])
                        remaining_lengths.append(current_stock_length - length - cutting_gap)

            total_used_length = sum(sum(p) for p in patterns)
            total_stock_length = current_stock_length * len(patterns)
            current_efficiency = total_used_length / total_stock_length if total_stock_length > 0 else 0

            if optimization_method == "Tối Ưu Hiệu Suất Cao Nhất":
                if current_efficiency > best_efficiency:
                    best_patterns = patterns
                    best_remaining_lengths = remaining_lengths
                    best_stock_length = current_stock_length
                    best_efficiency = current_efficiency
                    best_bar_count = len(patterns)
            else:
                if len(patterns) < best_bar_count or (len(patterns) == best_bar_count and current_efficiency > best_efficiency):
                    best_patterns = patterns
                    best_remaining_lengths = remaining_lengths
                    best_stock_length = current_stock_length
                    best_efficiency = current_efficiency
                    best_bar_count = len(patterns)

        # Tạo DataFrame patterns
        bar_number = 1
        used_ids = []
        for pattern, remaining in zip(best_patterns, best_remaining_lengths):
            used_length = best_stock_length - remaining
            efficiency = sum(pattern) / best_stock_length
            all_patterns.append({
                'Profile Code': profile_code,
                'Bar Number': bar_number,
                'Stock Length': best_stock_length,
                'Used Length': used_length,
                'Remaining Length': remaining,
                'Efficiency': efficiency,
                'Cutting Pattern': '+'.join(str(p) for p in pattern),
                'Pieces': len(pattern)
            })

            for length in pattern:
                unassigned = profile_data[
                    (profile_data['Length'] == length) &
                    (~profile_data['Item ID'].isin(used_ids))
                ]
                if not unassigned.empty:
                    item_id = unassigned.iloc[0]['Item ID']
                    used_ids.append(item_id)
                    all_results.append({
                        'Profile Code': profile_code,
                        'Item ID': item_id,
                        'Length': length,
                        'Bar Number': bar_number
                    })

            bar_number += 1

        total_bars = len(best_patterns)
        total_length_needed = sum(lengths)
        total_length_used = best_stock_length * total_bars
        avg_efficiency = np.mean([p['Efficiency'] for p in all_patterns if p['Profile Code'] == profile_code])

        all_summaries.append({
            'Profile Code': profile_code,
            'Total Pieces': len(lengths),
            'Total Bars Used': total_bars,
            'Total Length Needed (mm)': total_length_needed,
            'Total Stock Length (mm)': total_length_used,
            'Waste (mm)': total_length_used - total_length_needed - cutting_gap * (len(lengths) - total_bars),
            'Overall Efficiency': total_length_needed / total_length_used if total_length_used > 0 else 0
        })

        # Ghi lại mảnh sót
        unassigned = profile_data[~profile_data['Item ID'].isin(used_ids)]
        if not unassigned.empty:
            unassigned['Note'] = f"Sót lại cho mã {profile_code}"
            unassigned_total.append(unassigned)

    patterns_df = pd.DataFrame(all_patterns)
    summary_df = pd.DataFrame(all_summaries)
    result_df = pd.DataFrame(all_results)
    unassigned_df = pd.concat(unassigned_total) if unassigned_total else pd.DataFrame()

    return result_df, patterns_df, summary_df, unassigned_df
