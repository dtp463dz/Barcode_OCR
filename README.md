# Barcode & OCR Tool

Một ứng dụng máy tính mạnh mẽ được xây dựng bằng Python và giao diện đồ họa Tkinter, hỗ trợ quét mã vạch (Barcode), nhận dạng ký tự quang học (OCR) và quản lý quét lưới mã QR theo vùng cấu hình (QR Grid) phục vụ cho các hệ thống kiểm tra chất lượng sản phẩm trong môi trường công nghiệp. Hệ thống hỗ trợ kết nối trực tiếp với dòng camera công nghiệp Basler thông qua giao thức truyền thông GigE/USB.

---

## 📌 Tính năng chính

### 1. Quét Mã Vạch (Barcode Mode)
* **Phát hiện tự động:** Tự động phát hiện và giải mã các loại mã vạch chuẩn công nghiệp từ hình ảnh trực tiếp (Live Stream) hoặc từ file hình ảnh.
* **Xử lý ảnh nâng cao:** Sử dụng thuật toán `fastNlMeansDenoising` để giảm nhiễu hình ảnh, tăng tỉ lệ đọc thành công đối với các mã vạch bị mờ, nhòe hoặc xước.
* **Trực quan hóa:** Hiển thị khung bao (bounding box) quanh mã vạch cùng thông tin dữ liệu giải mã trực tiếp trên màn hình giao diện.
* **Lưu trữ lịch sử:** Tự động ghi nhận và hiển thị danh sách các mã vạch đã quét kèm mốc thời gian thực.

### 2. Nhận Diện Ký Tự (OCR Mode)
* **Công nghệ Deep Learning:** Tích hợp thư viện học sâu `EasyOCR` giúp nhận diện văn bản, chuỗi ký tự hoặc mã sản phẩm với độ chính xác cao.
* **Xuất dữ liệu:** Tự động xuất kết quả văn bản nhận diện ra file định dạng `.txt` vào thư mục lưu trữ hệ thống.

### 3. Quản Lý Quét Lưới Mã QR (QR Grid Mode - 22 mã)
* **Setup ROI (Auto):** Tự động phát hiện vị trí các mã QR trên sản phẩm/bo mạch để sinh ra lưới vùng quan tâm (ROI) ban đầu dựa trên số hàng và tổng số mã kỳ vọng.
* **Edit ROI:** Cung cấp giao diện đồ họa tương tác trực quan cho phép người dùng kéo thả, căn chỉnh tọa độ, thay đổi kích thước hoặc vẽ tay các vùng ROI riêng biệt.
* **Load/Save ROI Config:** Hỗ trợ lưu cấu hình tọa độ lưới ROI thành file `.txt` và nạp lại nhanh chóng, giúp đồng bộ cấu hình giữa các ca máy hoặc các dòng sản phẩm khác nhau.
* **Scan & Export:** Thực hiện quét đồng loạt tất cả các vùng ROI được thiết lập, phân tích trạng thái `OK`/`NG` (Không quét được) của từng mã QR và tự động xuất báo cáo hình ảnh (toàn cảnh, ảnh cắt theo dòng-cột, ảnh cắt riêng lẻ) kèm file log kết quả chi tiết.

---

## 📁 Cấu trúc Thư mục Dự án

```text
└── ./
    ├── Barcode_OCR_Tool.py      # File thực thi giao diện chính (Tkinter GUI, luồng camera)
    ├── Barcode_OCR_Tool.spec    # Cấu hình đóng gói ứng dụng bằng PyInstaller
    ├── BaslerControl.py         # Module điều khiển kết nối và bắt hình từ Camera Basler (pypylon)
    ├── barcode_reader.py        # Xử lý lọc nhiễu và giải mã Barcode bằng PyZbar
    ├── ocr_process.py           # Module gọi EasyOCR xử lý nhận diện văn bản
    ├── qr_scanner.py            # Giải mã QR trong vùng ROI và vẽ ký hiệu trạng thái lên ảnh
    ├── roi_manager.py           # Quản lý danh sách ROI, logic tự động tính toán lưới, đọc/ghi file txt
    ├── roi_editor.py            # Giao diện chỉnh sửa thủ công vị trí và kích thước các ROI
    ├── export_manager.py        # Logic xử lý cắt ảnh vùng QR và xuất báo cáo dữ liệu đầu ra
    ├── paddle_process.py        # Module bổ trợ (nếu có tích hợp PaddleOCR)
    ├── gen_code_QR.py           # Tiện ích bổ trợ tạo/sinh mã QR phục vụ test
    ├── c.py / s.py              # Các script cấu hình hoặc script chạy thử nghiệm ngắn
    └── build/                   # Thư mục chứa tài nguyên sau khi compile đóng gói