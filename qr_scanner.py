from datetime import datetime
import cv2
from pyzbar import pyzbar

"""
 Crop theo từng ROI rồi decode riêng cho từng vùng
 Tránh ảnh hưởng tới các mã khác
"""

def _decode_crop(crop):
    if crop is None or crop.size == 0:
        return None
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if crop.ndim == 3 else crop
    try:
        denoised = cv2.fastNlMeansDenoising(gray, h=5)
    except cv2.error:
        denoised = gray

    try:
        symbols = [pyzbar.ZBarSymbol.QRCODE]
        results = pyzbar.decode(denoised, symbols=symbols)
    except Exception:
        results = pyzbar.decode(denoised)

    if not results:
        _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        try:
            results = pyzbar.decode(thresh, symbols=[pyzbar.ZBarSymbol.QRCODE])
        except Exception:
            results = pyzbar.decode(thresh)

    return results[0] if results else None

# Quét QR cho từng ROI trong danh sách rois
def scan_rois(image, rois):
    h_img, w_img = image.shape[:2]
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    results = []
    for roi in rois:
        x, y, w, h = roi["x"], roi["y"], roi["width"], roi["height"]
        # giu ROI trong bien anh, tranh crop loi neu file config bi sua sai
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(w_img, x + w), min(h_img, y + h)

        entry = {
            "id": roi["id"], "row": roi.get("row"), "col": roi.get("col"),
            "x": x, "y": y, "width": w, "height": h,
            "data": "", "type": "", "status": "NG",
            "det_x": None, "det_y": None, "det_w": None, "det_h": None,
            "timestamp": now,
        }

        try:
            if x1 <= x0 or y1 <= y0:
                entry["data"] = "ROI khong hop le (nam ngoai anh)"
                results.append(entry)
                continue

            crop = image[y0:y1, x0:x1]
            found = _decode_crop(crop)
            if found is not None:
                dx, dy, dw, dh = found.rect
                entry.update({
                    "data": found.data.decode("utf-8", errors="replace"),
                    "type": str(found.type),
                    "status": "OK",
                    "det_x": x0 + dx, "det_y": y0 + dy,
                    "det_w": dw, "det_h": dh,
                })
            else:
                entry["data"] = ""
                entry["status"] = "NG"
        except Exception as e:
            # bat loi rieng cho tung ROI - khong de 1 ROI lam sap qua trinh quet
            entry["status"] = "NG"
            entry["data"] = f"Loi doc: {e}"

        # cap nhat lai vao chinh object roi (de GUI / file .txt phan anh
        # ket qua quet gan nhat, nhung KHONG dung vao x/y/w/h)
        roi["sn"] = entry["data"] if entry["status"] == "OK" else ""
        roi["status"] = entry["status"]

        results.append(entry)

    return results

# status view
def annotate_image(image, results):
    out = image.copy()
    for r in results:
        color = (0, 200, 0) if r["status"] == "OK" else (0, 0, 220)
        cv2.rectangle(out, (r["x"], r["y"]),
                      (r["x"] + r["width"], r["y"] + r["height"]), color, 2)
        label = f"{r['id']}"
        if r["status"] == "OK":
            label += f": {r['data'][:18]}"
        else:
            label += ": NG"
        cv2.putText(out, label, (r["x"], max(15, r["y"] - 6)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    return out
