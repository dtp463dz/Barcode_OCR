import math
from PIL import Image, ImageDraw
import qrcode


def create_paired_qr_grid(data_pairs, output_filename="qr_paired_grid.png"):
    # Cấu hình cố định theo yêu cầu: 4 hàng, 3 cột = 12 ô
    ROWS = 4
    COLS = 3
    TOTAL_CELLS = ROWS * COLS  # 12

    # Kích thước cấu hình (pixel)
    qr_size = 180  # Kích thước mỗi mã QR
    cell_padding = 15  # Khoảng cách giữa các thành phần trong ô
    grid_gap = 20  # Khoảng cách giữa các ô lớn với nhau

    # Một ô vuông lớn sẽ chứa: QR_xuôi + khoảng cách + QR_ngược
    cell_width = qr_size + (cell_padding * 2)
    cell_height = (qr_size * 2) + (cell_padding * 3)

    # Tính kích thước tổng thể của bức ảnh
    grid_width = COLS * cell_width + (COLS + 1) * grid_gap
    grid_height = ROWS * cell_height + (ROWS + 1) * grid_gap

    # Tạo ảnh nền trắng
    grid_image = Image.new("RGB", (grid_width, grid_height), "white")
    draw = ImageDraw.Draw(grid_image)

    # Đảm bảo danh sách dữ liệu có đủ 12 cặp (nếu thiếu sẽ tự bù bằng dữ liệu trống)
    while len(data_pairs) < TOTAL_CELLS:
        data_pairs.append(("Data trống A", "Data trống B"))

    # Vòng lặp vẽ 12 ô
    for index in range(TOTAL_CELLS):
        col_idx = index % COLS
        row_idx = index // COLS

        # Tọa độ góc trên bên trái của ô lớn thứ [index]
        cell_x = grid_gap + col_idx * (cell_width + grid_gap)
        cell_y = grid_gap + row_idx * (cell_height + grid_gap)

        # Vẽ viền mảnh xung quanh ô vuông lớn để dễ phân biệt (Tùy chọn)
        draw.rectangle(
            [cell_x, cell_y, cell_x + cell_width, cell_y + cell_height],
            outline="#FFFFFF",
            width=2,
        )

        # Lấy dữ liệu của cặp QR tương ứng
        data_up, data_down = data_pairs[index]

        # --- 1. TẠO VÀ VẼ MÃ QR XUÔI (NẰM TRÊN) ---
        qr1 = qrcode.QRCode(version=1, box_size=10, border=1)
        qr1.add_data(data_up)
        qr1.make(fit=True)
        img_qr1 = qr1.make_image(
            fill_color="black", back_color="white"
        ).convert("RGB")
        img_qr1 = img_qr1.resize((qr_size, qr_size))

        x_qr1 = cell_x + cell_padding
        y_qr1 = cell_y + cell_padding
        grid_image.paste(img_qr1, (x_qr1, y_qr1))

        # --- 2. TẠO VÀ VẼ MÃ QR NGƯỢC (NẰM DƯỚI, XOAY 180 ĐỘ) ---
        qr2 = qrcode.QRCode(version=1, box_size=10, border=1)
        qr2.add_data(data_down)
        qr2.make(fit=True)
        img_qr2 = qr2.make_image(
            fill_color="black", back_color="white"
        ).convert("RGB")
        img_qr2 = img_qr2.resize((qr_size, qr_size))

        # Xoay ngược mã QR thứ hai 180 độ
        img_qr2_inverted = img_qr2.rotate(180)

        x_qr2 = cell_x + cell_padding
        y_qr2 = (
            y_qr1 + qr_size + cell_padding
        )  # Đẩy xuống dưới mã QR thứ nhất
        grid_image.paste(img_qr2_inverted, (x_qr2, y_qr2))

    # Lưu kết quả
    grid_image.save(output_filename)
    print(f"Đã xuất ảnh lưới 4x3 (12 ô đối đỉnh) tại: {output_filename}")


# --- CẤU HÌNH DỮ LIỆU ĐẦU VÀO CHO 12 Ô ---
# Mỗi phần tử trong danh sách là một bộ (Nội_dung_QR_Xuôi, Nội_dung_QR_Ngược)
danh_sach_cap_qr = [
    (f"O {i} - QR Xuoi", f"O {i} - QR Nguoc") for i in range(1, 13)
]

# Bạn có thể sửa thủ công nội dung từng ô như thế này:
# danh_sach_cap_qr = [
#     ("Link_Xuoi_1", "Link_Nguoc_1"),
#     ("Sản phẩm 2", "Thông tin 2"),
#     # ... điền đủ cho các ô tiếp theo
# ]

# Chạy code
create_paired_qr_grid(danh_sach_cap_qr, "luoi_12_o_qr_doi_dinh.png")