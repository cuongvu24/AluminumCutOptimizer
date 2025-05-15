# README.md for AluminumCutOptimizer

## 🧩 Giới thiệu
AluminumCutOptimizer là một ứng dụng mã nguồn mở được phát triển bằng Python và Streamlit nhằm tối ưu hóa việc cắt thanh nhôm từ danh sách đơn hàng đầu vào. Ứng dụng hoạt động trên file Excel và giúp giảm lãng phí vật liệu.

## 🚀 Tính năng chính
- Nhập dữ liệu từ file Excel mẫu (`mau_nhap.xlsx`)
- Tối ưu cắt theo chiều dài và số lượng yêu cầu
- Xuất kết quả ra file Excel (`mau_xuat.xlsx`)
- Giao diện thân thiện bằng Streamlit

## 🛠 Cài đặt và chạy ứng dụng
```bash
# Bước 1: Clone repository
https://github.com/cuongvu24/AluminumCutOptimizer.git

# Bước 2: Cài đặt môi trường ảo (tuỳ chọn)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Bước 3: Cài đặt các thư viện cần thiết
pip install -r requirements.txt

# Bước 4: Chạy ứng dụng
streamlit run app.py
```

## 📂 Cấu trúc thư mục
```
AluminumCutOptimizer/
├── app.py
├── cutting_optimizer.py
├── utils.py
├── mau_nhap.xlsx
├── mau_xuat.xlsx
├── requirements.txt
└── README.md
```

## 🌐 Triển khai lên Streamlit Cloud
1. Push code lên GitHub
2. Vào https://streamlit.io/cloud và kết nối GitHub
3. Chọn repo → deploy → nhận link công khai

## 📄 Giấy phép
MIT License - Tự do sử dụng, chia sẻ và sửa đổi.

---

*Phát triển bởi Vũ Cường - hero9xhn@gmail.com*

---

### 📦 requirements.txt
```txt
streamlit
pandas
openpyxl
```
