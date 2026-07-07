import os
from datetime import datetime
import cv2

"""
Output:
    - Ảnh tổng thể (có vẽ toạ độ, xem được bằng Paint hay bất kỳ phần mềm nào)
    - Ảnh theo từng hàng / từng cột (cột = "cot o", 1 o co the co 2 mã)
    - Ảnh riêng lẻ từng mã QR
    - File .txt chứa ID, SN, X, Y, WIDTH, HEIGHT
"""

SEPARATOR = "----------------------------"

# vẽ tọa độ grid
def _draw_coordinate_grid(img, step = 50):
    out = img.copy()
    h, w = out.shape[:2]
    grid_color = (180,180,180)
    text_color = (0,0,0)
    for gx in range(0, w, step): 
        cv2.line(out, (gx, 0), (gx, h), grid_color, 1)
        cv2.putText(out, str(gx), (gx + 2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.35, text_color, 1)
    for gy in range(0, h, step):
        cv2.line(out, (0, gy), (w, gy), grid_color, 1)
        cv2.putText(out, str(gy), (2, gy + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.35, text_color, 1)
    return out

# overview, ảnh tổng thể: id, khung ROI, tọa độ, trạng thái 
def draw_overview(image, results, with_grid=True, grid_step = 100):
    out = _draw_coordinate_grid(image, grid_step) if with_grid else image.copy()
    for r in results:
        color = (0, 200, 0) if r["status"] == "OK" else (0, 0, 220)
        x, y, w, h = r["x"], r["y"], r["width"], r["height"]
        cv2.rectangle(out, (x, y), (x + w, y + h), color, 2)
        tag = f"{r['id']} ({x},{y})"
        cv2.putText(out, tag, (x, max(15, y - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    return out

def _bounding_box(rs, pad=15):
    xs0 = [r["x"] for r in rs]
    ys0 = [r["y"] for r in rs]
    xs1 = [r["x"] + r["width"] for r in rs]
    ys1 = [r["y"] + r["height"] for r in rs]
    return (max(0, min(xs0) - pad), max(0, min(ys0) - pad),
            max(xs1) + pad, max(ys1) + pad)

def _write_results_txt(path, results, ts):
    ok = sum(1 for r in results if r["status"] == "OK")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"Ket qua quet luc {ts} - {ok}/{len(results)} OK\n")
        for r in sorted(results, key=lambda r: int(r["id"])):
            f.write(SEPARATOR + "\n")
            f.write(f"ID: {r['id']}\n")
            f.write(f"SN: {r['data']}\n")
            f.write(f"STATUS: {r['status']}\n")
            f.write(f"ROW: {r['row']}\n")
            f.write(f"COL: {r['col']}\n")
            f.write(f"X: {r['x']}\n")
            f.write(f"Y: {r['y']}\n")
            f.write(f"WIDTH: {r['width']}\n")
            f.write(f"HEIGHT: {r['height']}\n")
        f.write(SEPARATOR + "\n")

# sinh ra toàn bộ file output
def export_all(image, results, roi_manager, out_root = "Result_QR"):
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    out_dir = os.path.join(out_root, ts)
    rows_dir = os.path.join(out_dir, "rows")
    cols_dir = os.path.join(out_dir, "cols")
    ind_dir = os.path.join(out_dir, "individual")
    for d in (out_dir, rows_dir, cols_dir, ind_dir):
        os.makedirs(d, exist_ok=True)
    # 1. Ảnh tổng quát
    overview = draw_overview(image, results)
    cv2.imwrite(os.path.join(out_dir, "overview.jpg"), overview)
    # 2. Ảnh theo hàng/cột -- ô
    by_row, by_col = {}, {}
    for r in results:
        by_row.setdefault(r["row"], []).append(r)
        by_col.setdefault(r["col"], []).append(r)

    for row_idx, rs in by_row.items():
        x0, y0, x1, y1 = _bounding_box(rs)
        cv2.imwrite(os.path.join(rows_dir, f"row_{row_idx}.jpg"), image[y0:y1, x0:x1])

    for col_idx, rs in by_col.items():
        x0, y0, x1, y1 = _bounding_box(rs)
        cv2.imwrite(os.path.join(cols_dir, f"col_{col_idx}.jpg"), image[y0:y1, x0:x1])

    # 3. Ảnh riêng theo từng mã
    for r in results:
        x0, y0 = max(0, r["x"]), max(0, r["y"])
        x1 = min(image.shape[1], r["x"] + r["width"])
        y1 = min(image.shape[0], r["y"] + r["height"])
        if x1 > x0 and y1 > y0:
            cv2.imwrite(os.path.join(ind_dir, f"{r['id']}.jpg"), image[y0:y1, x0:x1])
    
    # 4. File txt
    results_txt_path = os.path.join(out_dir, "results.txt")
    _write_results_txt(results_txt_path, results, ts)

    # 5) File .txt dung de HIEU CHINH (yeu cau #3) - dung mau ID/SN/X/Y/WIDTH/HEIGHT
    roi_config_path = os.path.join(out_dir, "roi_config.txt")
    roi_manager.save_txt(roi_config_path)

    return {
        "out_dir": out_dir,
        "overview": os.path.join(out_dir, "overview.jpg"),
        "results_txt": results_txt_path,
        "roi_config": roi_config_path,
    }