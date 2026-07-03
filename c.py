import cv2
from pyzbar import pyzbar

def Process_barcodes(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    barcodes = pyzbar.decode(gray)
    results = []
    annotated_image = image.copy()

    for barcode in barcodes:
        x, y, w, h = barcode.rect
        data = barcode.data.decode('utf-8')
        barcode_type = barcode.type
        length = len(data)

        results.append({
            'data': data,
            'type': barcode_type,
            'length': length,
            'rect': (x, y, w, h)
        })
        cv2.rectangle(annotated_image, (x, y), (x + w, y + h), (0, 255, 0), 3)
        label = f"{data} [{barcode_type}] Length:{length}"
        cv2.putText(annotated_image, label, (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

    return results, annotated_image