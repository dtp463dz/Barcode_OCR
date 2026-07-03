import cv2
from paddleocr import PaddleOCR
import os
from datetime import datetime

ocr = PaddleOCR(lang='en', use_gpu=True, show_log=False)

def process_ocr(image, save_dir="Result_OCR_Paddle", min_conf=0.5):
    os.makedirs(save_dir, exist_ok=True)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, h=5)
    result = ocr.ocr(denoised)
    full_text_lines = []
    if result:
        for line in result:
            for box, (text, conf) in line:
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
