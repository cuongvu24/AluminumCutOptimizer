import pandas as pd

def validate_input_excel(df):
    """ Kiểm tra file đầu vào cắt nhôm """
    required = ["Profile Code", "Length", "Quantity"]
    vn_map = {"Mã Thanh": "Profile Code", "Chiều Dài": "Length", "Số Lượng": "Quantity"}

    for vn, en in vn_map.items():
        if vn in df.columns:
            df.rename(columns={vn: en}, inplace=True)

    missing = [c for c in required if c not in df.columns]
    if missing:
        return False, f"Thiếu cột: {', '.join(missing)}"

    df.dropna(subset=["Profile Code", "Length", "Quantity"], inplace=True)

    try:
        df["Length"] = pd.to_numeric(df["Length"])
        df["Quantity"] = pd.to_numeric(df["Quantity"])
    except Exception:
        return False, "Cột Chiều Dài & Số Lượng phải là số"

    if (df["Length"] <= 0).any():
        return False, "Chiều Dài phải > 0"
    if (df["Quantity"] <= 0).any():
        return False, "Số Lượng phải > 0"

    return True, "Hợp lệ"

def create_output_excel(stream, result_df, patterns_df, summary_df, stock_length, cutting_gap, unassigned_df=None):
    """ Xuất file Excel kết quả tối ưu """
    summary_out = summary_df.copy()
    summary_out.columns = [
        "Mã Thanh", "Tổng Số Đoạn", "Tổng Thanh Sử Dụng",
        "Tổng Chiều Dài Cần (mm)", "Tổng Chiều Dài Thanh (mm)",
        "Phế Liệu (mm)", "Hiệu Suất Tổng Thể"
    ]

    patterns_out = patterns_df.copy()
    patterns_out.columns = [
        "Mã Thanh", "Số Thanh", "Chiều Dài Thanh",
        "Chiều Dài Sử Dụng", "Chiều Dài Còn Lại",
        "Hiệu Suất", "Mẫu Cắt", "Số Đoạn Cắt"
    ]

    result_out = result_df.copy()
    result_out.columns = ["Mã Thanh", "Mã Mảnh", "Chiều Dài", "Số Thanh"]

    with pd.ExcelWriter(stream, engine="openpyxl") as writer:
        summary_out.to_excel(writer, sheet_name="Tổng Hợp", index=False)
        patterns_out.to_excel(writer, sheet_name="Mẫu Cắt", index=False)
        result_out.to_excel(writer, sheet_name="Chi Tiết Mảnh", index=False)

        if unassigned_df is not None and not unassigned_df.empty:
            unassigned_df.to_excel(writer, sheet_name="Sót Lại", index=False)

        params = pd.DataFrame({
            "Tham Số": ["Chiều Dài Tiêu Chuẩn", "Khoảng Cách Cắt"],
            "Giá Trị": [stock_length, cutting_gap]
        })
        params.to_excel(writer, sheet_name="Tham Số", index=False)
