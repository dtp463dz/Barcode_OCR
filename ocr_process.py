import cv2
import easyocr
import os
from datetime import datetime

reader = easyocr.Reader(['en', 'vi'], gpu=True)

def process_ocr(image, save_dir="Result_OCR", min_conf=0.5):
    os.makedirs(save_dir, exist_ok=True)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, h=10)
    _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    processed = cv2.dilate(thresh, kernel, iterations=1)
    results = reader.readtext(processed, detail=1, paragraph=False)

    full_text_lines = []
    for bbox, text, conf in results:
        if conf >= min_conf:  
            full_text_lines.append(text.strip())

    full_text = "\n".join(full_text_lines) if full_text_lines else ""

    txt_path = None
    if full_text.strip():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        txt_path = os.path.join(save_dir, f"{timestamp}_ocr_result.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(full_text)

    return full_text, txt_path, image.copy()