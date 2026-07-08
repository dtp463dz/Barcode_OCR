import os
import cv2
import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from PIL import Image, ImageTk
import threading
from time import sleep
from datetime import datetime
from BaslerControl import CamControl
from barcode_reader import Process_barcodes
from ocr_process import process_ocr

from roi_manager import ROIManager
from roi_editor import ROIEditor
from qr_scanner import scan_rois, annotate_image
from export_manager import export_all

class BarcodeOCRTool:
    def __init__(self, root):
        self.root = root
        self.root.title("Barcode & OCR Tool - Debug")
        self.root.geometry("1400x800")
        self.cam = CamControl()
        self.camera_connected = False
        self.preview_thread = None
        self.running_preview = False
        self.current_img = None
        self.barcode_history = []

        # --- state cho QR Grid (yeu cau ROI 22 ma) -------------------
        self.roi_manager = ROIManager()
        self.last_scan_results = []
        self.last_export_dir = None

        self.function_var = tk.StringVar(value="Barcode")
        self.function_var.trace("w", self.on_function_change)
        self.setup_gui()
        self.root.bind('<Return>', self.process_on_enter)

    def setup_gui(self):
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(1, weight=1)

        top_frame = tk.Frame(self.root)
        top_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=10)

        tk.Label(top_frame, font=("Arial", 12)).grid(row=0, column=0, padx=(0), sticky="e")
        self.function_menu = tk.OptionMenu(top_frame, self.function_var, "Barcode", "OCR", "QR Grid")
        self.function_menu.config(font=("Arial", 12), width=10, height=2)
        self.function_menu.grid(row=0, column=1, padx=5, sticky="w")

        self.connect_button = tk.Button(top_frame, text="Connect Camera", font=("Arial", 12), height=2,
                                        command=self.toggle_camera_preview)
        self.connect_button.grid(row=0, column=2, padx=5, sticky="w")

        tk.Button(top_frame, text="Load image from File", font=("Arial", 12), height=2,
                  command=self.load_from_file).grid(row=0, column=3, padx=5, sticky="w")

        self.result_frame = tk.Frame(self.root)
        self.result_frame.grid(row=1, column=0, sticky="ns", padx=10, pady=0)
        self.result_frame.grid_rowconfigure(0, weight=1)
        self.result_frame.grid_columnconfigure(0, weight=1)

        self.barcode_frame = tk.Frame(self.result_frame)
        tk.Label(self.barcode_frame, text="Barcode Results:", font=("Arial", 13)).pack(anchor="w")
        clear_btn = tk.Button(self.barcode_frame, text="Clear", font=("Arial", 10, "bold"),
                      command=self.clear_barcode_history, bg="#d32f2f", fg="white", relief="flat", padx=10)
        clear_btn.pack(anchor="e", pady=(0, 10))
        self.barcode_text = tk.Text(self.barcode_frame, height=30, font=("Arial", 11))
        self.barcode_text.pack(fill=tk.BOTH, expand=True)

        self.ocr_frame = tk.Frame(self.result_frame)
        tk.Label(self.ocr_frame, text="OCR Result:", font=("Arial", 13, "bold")).pack(anchor="w")
        self.ocr_label = tk.Label(self.ocr_frame, text="No OCR yet", fg="blue", font=("Arial", 12))
        self.ocr_label.pack(anchor="w", pady=5)
        self.ocr_text = tk.Text(self.ocr_frame, height=30, font=("Arial", 11))
        self.ocr_text.pack(fill=tk.BOTH, expand=True)

        # ---------------- QR Grid panel (MOI) ----------------
        self.qr_frame = tk.Frame(self.result_frame)
        tk.Label(self.qr_frame, text="QR Grid (22 ma):", font=("Arial", 13, "bold")).pack(anchor="w")

        qr_btns = tk.Frame(self.qr_frame)
        qr_btns.pack(fill=tk.X, pady=(0, 8))
        tk.Button(qr_btns, text="1. Setup ROI (Auto)", command=self.setup_roi_auto,
                  bg="#1565c0", fg="white").pack(fill=tk.X, pady=2)
        tk.Button(qr_btns, text="2. Edit ROI", command=self.edit_roi).pack(fill=tk.X, pady=2)
        tk.Button(qr_btns, text="3. Load ROI Config...", command=self.load_roi_config).pack(fill=tk.X, pady=2)
        tk.Button(qr_btns, text="4. Scan && Export", command=self.scan_and_export,
                  bg="#2e7d32", fg="white").pack(fill=tk.X, pady=2)

        self.qr_summary_var = tk.StringVar(value="Chua co ROI nao. Bat dau tu buoc 1.")
        tk.Label(self.qr_frame, textvariable=self.qr_summary_var, fg="#333", wraplength=260,
                 justify="left").pack(anchor="w", pady=(0, 6))

        self.qr_text = tk.Text(self.qr_frame, height=24, font=("Consolas", 10))
        self.qr_text.pack(fill=tk.BOTH, expand=True)

        self.barcode_frame.grid(row=0, column=0, sticky="nsew")
        self.ocr_frame.grid_remove()
        self.qr_frame.grid_remove()

        right_panel = tk.Frame(self.root)
        right_panel.grid(row=1, column=1, sticky="nsew", padx=10, pady=0)
        self.img_label = tk.Label(right_panel,
                                  font=("Arial", 20), fg="white", bg="#8be7a3", compound="center")
        self.img_label.pack(fill=tk.BOTH, expand=True)
        log_frame = tk.Frame(self.root)
        log_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=10)

        tk.Label(log_frame, text="Log:", font=("Arial", 13)).pack(anchor="w")
        log_inner = tk.Frame(log_frame)
        log_inner.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(log_inner, height=8, font=("Arial", 11), bg="#f0f0f0")
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        log_scroll = tk.Scrollbar(log_inner, command=self.log_text.yview)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=log_scroll.set)

    def on_function_change(self, *args):
        mode = self.function_var.get()
        self.barcode_frame.grid_remove()
        self.ocr_frame.grid_remove()
        self.qr_frame.grid_remove()
        if mode == "Barcode":
            self.barcode_frame.grid(row=0, column=0, sticky="nsew")
        elif mode == "OCR":
            self.ocr_frame.grid(row=0, column=0, sticky="nsew")
        else:
            self.qr_frame.grid(row=0, column=0, sticky="nsew")

    def log(self, msg):
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)

    def clear_barcode_history(self):
        self.barcode_history = []
        self.barcode_text.delete(1.0, tk.END)

    def toggle_camera_preview(self):
        if not self.camera_connected:
            status = self.cam.Connect()
            if status == 'OK':
                self.camera_connected = True
                self.connect_button.config(text="Disconnect Camera")
                self.running_preview = True
                self.preview_thread = threading.Thread(target=self.preview_loop, daemon=True)
                self.preview_thread.start()
                self.log("Camera connected - live preview started!")
            else:
                self.log(f"Camera connect failed: {status}")
        else:
            self.running_preview = False
            if self.preview_thread:
                self.preview_thread.join(timeout=2.0)
            self.cam.DisConnect()
            self.camera_connected = False
            self.connect_button.config(text="Connect Camera")
            self.img_label.config(image='')
            self.log("Camera disconnected")

    def preview_loop(self):
        while self.running_preview:
            img = self.cam.GrabImg()
            if img is not None:
                self.current_img = img.copy()
                preview_img = img.copy()
                mode = self.function_var.get()
                if mode == "Barcode":
                    _, preview_img = Process_barcodes(preview_img)
                else:
                    # OCR va QR Grid: chi xu ly khi nguoi dung bam Enter /
                    # cac nut tuong ung (tranh decode lien tuc lam giat lag)
                    preview_img = img.copy()
                self.update_preview_img(preview_img)
            sleep(0.03)

    def update_preview_img(self, img_cv):
        if img_cv is None:
            self.img_label.config(image='', bg="#8be7a3", fg="white")
            return

        height, width = img_cv.shape[:2]
        label_width = self.img_label.winfo_width()
        label_height = self.img_label.winfo_height()

        if label_width < 10 or label_height < 10:
            label_width, label_height = 900, 700

        scale = min(label_width / width, label_height / height)
        new_width = int(width * scale)
        new_height = int(height * scale)
        resized = cv2.resize(img_cv, (new_width, new_height))
        canvas = np.full((label_height, label_width, 3), (240, 240, 240), dtype=np.uint8)
        y_offset = (label_height - new_height) // 2
        x_offset = (label_width - new_width) // 2
        canvas[y_offset:y_offset + new_height, x_offset:x_offset + new_width] = resized

        img_rgb = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(img_rgb)
        img_tk = ImageTk.PhotoImage(img_pil)

        self.img_label.config(image=img_tk, text="", bg="#f0f0f0")
        self.img_label.image = img_tk

    def process_on_enter(self, event):
        if self.current_img is None:
            messagebox.showwarning("Warning", "No image! Connect camera or load file first.")
            return

        mode = self.function_var.get()
        result_img = self.current_img.copy()

        if mode == "Barcode":
            barcode_results, result_img = Process_barcodes(result_img)
            for res in barcode_results:
                info = f"[{datetime.now().strftime('%H:%M:%S')}] Data: {res['data']} | Type: {res['type']} | Lenght: {res['length']}"
                self.barcode_history.append(info)
            self.barcode_text.delete(1.0, tk.END)
            self.barcode_text.insert(tk.END, "\n".join(self.barcode_history))
            self.log(f"Barcode: Found {len(barcode_results)} new code(s)")
        elif mode == "OCR":
            ocr_text, txt_path, _ = process_ocr(result_img, min_conf=0.5)
            self.ocr_text.delete(1.0, tk.END)
            self.ocr_text.insert(tk.END, ocr_text)

            if txt_path:
                messagebox.showinfo("OCR Pass!", f"Text has been recognized and saved.:\n{txt_path}")
                self.ocr_label.config(text=f"Saved: {os.path.basename(txt_path)}")
                self.log(f"OCR Pass → {os.path.basename(txt_path)}")
            else:
                messagebox.showerror("OCR Fail", "No text was identified.")
                self.ocr_label.config(text="OCR Fail")
                self.log("OCR Fail - No reliable text detected")

            result_img = self.current_img.copy()
        else:
            # QR Grid: Enter = quet nhanh (khong xuat file), dung nut
            # "Scan && Export" de xuat day du anh/file .txt.
            self._run_scan(export=False)
            return

        self.update_preview_img(result_img)

    def load_from_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp")])
        if file_path:
            img = cv2.imread(file_path)
            if img is not None:
                self.current_img = img.copy()
                self.update_preview_img(img)
                self.log(f"Loaded: {os.path.basename(file_path)}")

    # =====================================================================
    # QR GRID - cac ham xu ly rieng cho che do 22 ma QR
    # =====================================================================
    def setup_roi_auto(self):
        """Buoc 1: auto-detect toan bo QR tren anh hien tai -> sinh ROI ban dau,
        sau do mo luon ROI Editor de nguoi dung chinh tay (theo lua chon cua ban:
        'Ca hai: auto-detect truoc, chinh tay ngay sau')."""
        if self.current_img is None:
            messagebox.showwarning("Warning", "Chua co anh! Ket noi camera hoac Load image from File truoc.")
            return

        rows = simpledialog.askinteger("Setup ROI", "So hang (rows) uoc luong:",
                                        initialvalue=4, minvalue=1, maxvalue=20, parent=self.root)
        if rows is None:
            return
        count = simpledialog.askinteger("Setup ROI", "Tong so ma QR ky vong:",
                                         initialvalue=22, minvalue=1, maxvalue=200, parent=self.root)
        if count is None:
            return
        margin_pct = simpledialog.askinteger(
            "Setup ROI",
            "Do nong ROI so voi ma QR (%)\n"
            "0 = khit sat mep ma QR (de sai neu board xe dich)\n"
            "8-15 = khuyen nghi (chiu duoc xe dich nhe)",
            initialvalue=8, minvalue=0, maxvalue=100, parent=self.root)
        if margin_pct is None:
            return

        found = self.roi_manager.auto_detect(self.current_img, expected_rows=rows,
                                              expected_count=count, margin_ratio=margin_pct / 100.0)
        self.log(f"Auto-detect: tim thay {len(found)}/{count} ma QR, da sinh {len(found)} ROI.")
        self._refresh_qr_summary()
        self.edit_roi()

    def edit_roi(self):
        if self.current_img is None:
            messagebox.showwarning("Warning", "Chua co anh de hien thi trong ROI Editor.")
            return
        if not self.roi_manager.rois:
            if not messagebox.askyesno("QR Grid", "Chua co ROI nao. Mo cua so trong de tu ve tay?"):
                return
        ROIEditor(self.root, self.current_img, self.roi_manager, on_save=self._on_roi_editor_saved)

    def _on_roi_editor_saved(self, roi_manager):
        self.roi_manager = roi_manager
        self._refresh_qr_summary()
        self.log(f"Da cap nhat ROI qua Editor: {len(self.roi_manager.rois)} ROI.")

    def load_roi_config(self):
        path = filedialog.askopenfilename(filetypes=[("Text config", "*.txt")])
        if not path:
            return
        try:
            if not self.roi_manager.rois:
                self.roi_manager.load_txt(path)
                self.log(f"Da nap ROI config: {path} ({len(self.roi_manager.rois)} ROI)")
            else:
                info = self.roi_manager.update_from_txt(path)
                self.log(f"Da hop nhat config: doi {len(info['changed'])} ROI "
                         f"({info['changed']}), them {len(info['added'])} ROI moi.")
                if info["missing"]:
                    self.log(f"[CANH BAO] {len(info['missing'])} ROI khong co trong file, da GIU NGUYEN.")
        except Exception as e:
            messagebox.showerror("Load ROI Config", f"Loi doc file: {e}")
            return
        self._refresh_qr_summary()

    def scan_and_export(self):
        self._run_scan(export=True)

    def _run_scan(self, export=False):
        """Buoc 4: quet tat ca ROI tren anh hien tai; neu export=True thi sinh
        day du anh tong the / theo hang-cot / rieng le + file .txt."""
        if self.current_img is None:
            messagebox.showwarning("Warning", "Chua co anh! Ket noi camera hoac Load image from File truoc.")
            return
        if not self.roi_manager.rois:
            messagebox.showwarning("Warning", "Chua co ROI nao. Lam buoc 1 (Setup ROI) truoc.")
            return

        results = scan_rois(self.current_img, self.roi_manager.rois)
        self.last_scan_results = results
        annotated = annotate_image(self.current_img, results)
        self.update_preview_img(annotated)

        ok = sum(1 for r in results if r["status"] == "OK")
        self.qr_summary_var.set(f"Ket qua: {ok}/{len(results)} OK")
        self.qr_text.delete(1.0, tk.END)
        for r in results:
            self.qr_text.insert(tk.END, f"[{r['status']:>2}] {r['id']:<8} "
                                        f"({r['x']},{r['y']}) '{r['data']}'\n")
        self.log(f"QR Grid Scan: {ok}/{len(results)} OK")

        if export:
            out = export_all(self.current_img, results, self.roi_manager)
            self.last_export_dir = out["out_dir"]
            self.log(f"Da xuat ket qua vao: {out['out_dir']}")
            messagebox.showinfo("Scan && Export",
                                 f"Da quet {ok}/{len(results)} OK.\nDa luu vao:\n{out['out_dir']}")

    def _refresh_qr_summary(self):
        n = len(self.roi_manager.rois)
        self.qr_summary_var.set(f"Dang co {n} ROI. San sang de Scan && Export.")


if __name__ == "__main__":
    root = tk.Tk()
    app = BarcodeOCRTool(root)
    root.mainloop()