import pandas as pd
import json
import uuid
import os
from datetime import datetime

def create_output_excel(output_stream, result_df, patterns_df, summary_df, stock_length_options, cutting_gap):
    with pd.ExcelWriter(output_stream, engine='openpyxl') as writer:
        result_df.to_excel(writer, sheet_name="Chi Tiết Mảnh Cắt", index=False)
        patterns_df.to_excel(writer, sheet_name="Danh Sách Mẫu Cắt", index=False)
        summary_df.to_excel(writer, sheet_name="Tổng Hợp Hiệu Suất", index=False)
        pd.DataFrame({
            'Tham Số': ['Kích Thước Thanh', 'Khoảng Cách Cắt'],
            'Giá Trị': [', '.join(map(str, stock_length_options)), str(cutting_gap)]
        }).to_excel(writer, sheet_name="Tham Số Tối Ưu", index=False)

def save_optimization_history(result_df, patterns_df, summary_df, stock_length_options, cutting_gap, optimization_method, name=None):
    history_data = load_optimization_history()
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # Kiểm tra tên rỗng, dùng timestamp nếu không có tên
    entry_name = name.strip() if name and name.strip() else timestamp
    entry = {
        'id': str(uuid.uuid4()),
        'name': entry_name,  # Lưu tên người dùng nhập
        'timestamp': timestamp,
        'result_df': result_df.to_dict(),
        'patterns_df': patterns_df.to_dict(),
        'summary_df': summary_df.to_dict(),
        'stock_length_options': stock_length_options,
        'cutting_gap': cutting_gap,
        'optimization_method': optimization_method,
        'profile_codes': sorted(summary_df['Mã Thanh'].unique().tolist())
    }
    history_data.append(entry)
    with open("history.json", 'w', encoding='utf-8') as f:
        json.dump(history_data, f, ensure_ascii=False, indent=2)

def load_optimization_history():
    if os.path.exists("history.json"):
        try:
            with open("history.json", 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def delete_optimization_history_entry(entry_id):
    history_data = load_optimization_history()
    history_data = [entry for entry in history_data if entry['id'] != entry_id]
    with open("history.json", 'w', encoding='utf-8') as f:
        json.dump(history_data, f, ensure_ascii=False, indent=2)
