import os
import re
from datetime import datetime
import cv2
import numpy as np
from pyzbar import pyzbar


# I) Schema
#   id       : str   - định danh duy nhất, ví dụ "R1C1" (Row 1, Column 1)
#   row      : int   - hàng, suy ra từ vị trí auto-detect
#   col      : int   - cột trong hàng đó
#   x, y     : int   - tọa độ góc trên-trái của ROI (pixel, trên ảnh gốc)
#   width    : int   - chiều rộng của ROI
#   height   : int   - chiều cao của ROI
#   sn      : str  - noi dung QR ("Serial Number") doc duoc lan quet gan nhat
#   status  : str  - "OK" / "NG" / "UNSCANNED"

# Nội dung mỗi id, cách nhau bởi 1 dòng gạch ngang
#  Ví dụ: 
#   ----------------------------
#   ID: 1
#   SN: ABC123XYZ
#   X: 48
#   Y: 48
#   WIDTH: 93
#   HEIGHT: 93
#   ----------------------------

# STATUS/ROW/COL được ghi thêm vào file (để người đọc theo dõi)
# nhưng khi đọc lại file 3 trường hợp này bị bỏ qua và tự động tính lại
# tránh trường hợp người dùng sửa nhầm lẫn sai lệch dữ liệu group hàng/cột

EDITABLE_FIELDS = ("x", "y", "width", "height")  # trường hợp có thể sửa
SEPARATOR = "----------------------------"

def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

class ROIManager:
    def __init__(self):
        self.rois = []
        self.meta = {}

    # II) AUTO-DETECT: quét toàn bộ ảnh 1 lần, gồm nhóm hàng/ô, ID
    def auto_detect(self, image, expected_rows=4, expected_count=22, margin_ratio=0.25):    
        """
        expected_rows : số hàng ước lượng (mặc định 4)
        expected_count : tổng số mã QR kỳ vọng (chỉ để cảnh báo nếu thiếu).
        margin_ratio : ROI rộng hơn boudingbox QR thực tế bao nhiêu % để scan ổn định hơn khi bản xê dịch
        Trả về: List ROI mới tạo (cũng được lưu vào self.rois)
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
        denoised = cv2.fastNlMeansDenoising(gray, h=5)
        try:
            symbols = [pyzbar.ZBarSymbol.QRCODE]
            decoded = pyzbar.decode(denoised, symbols=symbols)
        except Exception:
            decoded = pyzbar.decode(denoised)

        if not decoded:
            return []

        boxes = []
        for d in decoded:
            x, y, w, h = d.rect
            boxes.append({
                "x": x, "y": y, "w": w, "h": h,
                "cx": x + w / 2.0, "cy": y + h / 2.0,
                "sn": d.data.decode("utf-8", errors="replace"),
            })

        if len(decoded) < expected_count:
            print(f"[CANH BAO] Chi tim thay {len(decoded)}/{expected_count} ma QR "
                  f"trong lan auto-detect. Ban co the them ROI con thieu bang tay "
                  f"trong ROI Editor.")

        self.rois = self._build_grid(boxes, expected_rows, margin_ratio)
        h_img, w_img = image.shape[:2]
        self.meta = {"created": _now(), "updated": _now(),
                     "image_width": w_img, "image_height": h_img,
                     "expected_count": expected_count}
        return self.rois
    
    # xây dựng grid: lưới hàng/ô, đánh ID liên tục theo hàng (trai->phai, trên->dưới)
    def _build_grid(self, boxes, expected_rows, margin_ratio):
        row_labels = self._cluster_1d([b["cy"] for b in boxes], k=expected_rows)
        rows = {}
        for b, r in zip(boxes, row_labels):
            rows.setdefault(r, []).append(b)
        row_order = sorted(rows.keys(), key=lambda r: np.mean([b["cy"] for b in rows[r]]))

        new_rois = []
        global_id = 1
        for row_idx, r in enumerate(row_order, start=1):
            row_boxes = sorted(rows[r], key=lambda b: b["cx"])  # trai -> phai
            col_of_box = self._assign_cells(row_boxes)  # 2 mã cạnh nhau -> cùng 1 "cot o"
            for b, col_idx in zip(row_boxes, col_of_box):
                mx = int(b["w"] * margin_ratio)
                my = int(b["h"] * margin_ratio)
                roi = {
                    "id": str(global_id),
                    "row": row_idx,
                    "col": col_idx,
                    "x": max(0, b["x"] - mx),
                    "y": max(0, b["y"] - my),
                    "width": b["w"] + 2 * mx,
                    "height": b["h"] + 2 * my,
                    "sn": b.get("sn", ""),
                    "status": "OK" if b.get("sn") else "UNSCANNED",
                }
                new_rois.append(roi)
                global_id += 1
        return new_rois
    
    # đánh dấu các mã cùng ô hay khác ô khi ngược chiều mã 
    @staticmethod
    def _assign_cells(row_boxes_sorted_by_cx, gap_ratio = 1.6):
        if not row_boxes_sorted_by_cx:
            return []
        widths = [b["w"] for b in row_boxes_sorted_by_cx]
        avg_w = float(np.mean(widths))
        cols = [1]
        cell_idx = 1
        for prev, cur in zip(row_boxes_sorted_by_cx, row_boxes_sorted_by_cx[1:]):
            gap = cur["cx"] - prev["cx"]
            if gap > avg_w * gap_ratio:
                cell_idx += 1
            cols.append(cell_idx)
        return cols
    
    # gom tọa độ thành k nhóm, trả về list nhãn cùng độ dài với values
    @staticmethod
    def _cluster_1d(values, k, n_iter=25):
        values = np.array(values, dtype=float)
        k = max(1, min(k, len(values)))
        centroids = np.percentile(values, np.linspace(0, 100, k))
        labels = np.zeros(len(values), dtype=int)
        for i in range(n_iter):
            dist = np.abs(values[:, None] - centroids[None, :])
            new_labels = np.argmin(dist, axis=1)
            if np.array_equal(new_labels, labels) and i > 0:
                labels = new_labels
                break
            labels = new_labels
            for c in range(k):
                pts = values[labels == c]
                if len(pts) > 0:
                    centroids[c] = pts.mean()
        return labels.tolist()
    
    # Tính lại row, col cho toàn bộ self.rois dựa trên tọa độ hiện tại (x, y, width, height)
    def _infer_grid(self, expected_rows = 4):
        if not self.rois:
            return 
        boxes = [{"cx": r["x"] + r["width"] / 2.0, "cy": r["y"] + r["height"] / 2.0,
                  "w": r["width"], "_ref": r} for r in self.rois]
        row_labels = self._cluster_1d([b["cy"] for b in boxes], k=expected_rows)
        rows = {}
        for b, rl in zip(boxes, row_labels):
            rows.setdefault(rl, []).append(b)
        row_order = sorted(rows.keys(), key=lambda rl: np.mean([b["cy"] for b in rows[rl]]))
        for row_idx, rl in enumerate(row_order, start=1):
            row_boxes = sorted(rows[rl], key=lambda b: b["cx"])
            cols = self._assign_cells(row_boxes)
            for b, col_idx in zip(row_boxes, cols):
                b["_ref"]["row"] = row_idx
                b["_ref"]["col"] = col_idx

    # III) Lưu/Đọc file .txt
    def save_txt(self, path):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        ordered = sorted(self.rois, key=lambda r: int(r["id"]))
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# Cap nhat: {_now()} | Tong so ROI: {len(ordered)}\n")
            for r in ordered:
                f.write(SEPARATOR + "\n")
                f.write(f"ID: {r['id']}\n")
                f.write(f"SN: {r.get('sn', '')}\n")
                f.write(f"STATUS: {r.get('status', 'UNSCANNED')}\n")
                f.write(f"ROW: {r.get('row', '')}\n")
                f.write(f"COL: {r.get('col', '')}\n")
                f.write(f"X: {r['x']}\n")
                f.write(f"Y: {r['y']}\n")
                f.write(f"WIDTH: {r['width']}\n")
                f.write(f"HEIGHT: {r['height']}\n")
            f.write(SEPARATOR + "\n")
        return path

    @staticmethod
    def _parse_txt_blocks(path):
        blocks = {}
        current = None
        with open(path, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                if re.fullmatch(r"-{3,}", line):
                    current = None
                    continue
                if ":" not in line:
                    continue
                key, _, value = line.partition(":")
                key = key.strip().upper()
                value = value.strip()

                if key == "ID":
                    current = {}
                    blocks[value] = current
                    continue
                if current is None:
                    continue  # dong nam ngoai 1 khoi ID hop le -> bo qua

                if key == "SN":
                    current["sn"] = value
                elif key in ("X", "Y", "WIDTH", "HEIGHT"):
                    try:
                        current[key.lower()] = int(float(value))
                    except ValueError:
                        pass  # de trong / khong phai so -> bo qua, khong crash
                # STATUS/ROW/COL: co doc duoc cung khong dung, se tu tinh lai
        return blocks
    
    # IV) Hợp nhất file .txt đã chỉnh sửa
    # Có thể chỉnh sửa X/Y/Width/Height của ROI bị lệch
    # Tra ve: dict {"changed":[...], "added":[...], "missing":[...]}
    def update_from_txt(self, path, expected_rows = 4):
        new_blocks = self._parse_txt_blocks(path)
        existing_by_id = {r["id"]: r for r in self.rois}
        changed, added = [], []

        for rid, b in new_blocks.items():
            if not all(k in b for k in ("x", "y", "width", "height")):
                print(f"[CANH BAO] Bo qua ID {rid}: thieu x/y/width/height trong file.")
                continue
            new_vals = {"x": b["x"], "y": b["y"], "width": b["width"], "height": b["height"]}
            if rid in existing_by_id:
                old_r = existing_by_id[rid]
                did_change = any(new_vals[f] != old_r.get(f) for f in EDITABLE_FIELDS)
                if did_change:
                    old_r.update(new_vals)
                    changed.append(rid)
            else:
                self.rois.append({
                    "id": rid, "row": 0, "col": 0, **new_vals,
                    "sn": "", "status": "UNSCANNED",
                })
                added.append(rid)

        missing = [rid for rid in existing_by_id if rid not in new_blocks]
        if missing:
            print(f"[CANH BAO] {len(missing)} ROI vang mat trong file vua doc "
                  f"({missing}); cac ROI nay duoc GIU NGUYEN, khong bi xoa.")

        self._infer_grid(expected_rows)
        self.meta["updated"] = _now()
        return {"changed": changed, "added": added, "missing": missing}

    def get(self, roi_id):
        for r in self.rois:
            if r["id"] == roi_id:
                return r
        return None
    
    # Thêm hoặc sửa ROI (dùng cho ROI Editor)
    def upsert_manual(self, roi_id, x, y, widht, height, row=None, col=None):
        r = self.get(roi_id)
        if r is None:
            r = {"id": roi_id, "row": row or 0, "col": col or 0,
                 "sn": "", "status": "UNSCANNED"}
            self.rois.append(r)
        r.update({"x": int(x), "y": int(y), "width": int(width), "height": int(height)})
        self._infer_grid()
        return r
    
    def delete(self, roi_id):
        self.rois = [r for r in self.rois if r["id"] != roi_id]

    def next_free_id(self):
        used = [int(r["id"]) for r in self.rois if str(r["id"]).isdigit()]
        return str((max(used) + 1) if used else 1)
        
