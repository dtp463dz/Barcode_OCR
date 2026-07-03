import os
import cv2
import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import threading
from time import sleep
from datetime import datetime
from BaslerControl import CamControl
from barcode_reader import Process_barcodes
from ocr_process import process_ocr

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
        self.function_var = tk.StringVar(value="Barcode")
        self.function_var.trace("w", self.on_function_change)  
        self.setup_gui()
        self.root.bind('<Return>', self.process_on_enter)

    def setup_gui(self):
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(1, weight=1)

        top_frame = tk.Frame(self.root)
        top_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=10)

        tk.Label(top_frame, font=("Arial", 12)).grid(row=0, column=0, padx=(0),sticky="e")
        self.function_menu = tk.OptionMenu(top_frame, self.function_var, "Barcode", "OCR")
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
        clear_btn.pack(anchor="e", pady=(0,10))
        self.barcode_text = tk.Text(self.barcode_frame, height=30, font=("Arial", 11))
        self.barcode_text.pack(fill=tk.BOTH, expand=True)

        self.ocr_frame = tk.Frame(self.result_frame)
        tk.Label(self.ocr_frame, text="OCR Result:", font=("Arial", 13, "bold")).pack(anchor="w")
        self.ocr_label = tk.Label(self.ocr_frame, text="No OCR yet", fg="blue", font=("Arial", 12))
        self.ocr_label.pack(anchor="w", pady=5)
        self.ocr_text = tk.Text(self.ocr_frame, height=30, font=("Arial", 11))
        self.ocr_text.pack(fill=tk.BOTH, expand=True)

        self.barcode_frame.grid(row=0, column=0, sticky="nsew")
        self.ocr_frame.grid_remove()

        right_panel = tk.Frame(self.root)
        right_panel.grid(row=1, column=1, sticky="nsew", padx=10, pady=0)
        # self.img_label = tk.Label(right_panel, bg="#8be7a3")
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
        if mode == "Barcode":
            self.ocr_frame.grid_remove()
            self.barcode_frame.grid(row=0, column=0, sticky="nsew")
        else:
            self.barcode_frame.grid_remove()
            self.ocr_frame.grid(row=0, column=0, sticky="nsew")

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
                    preview_img = img.copy()
                self.update_preview_img(preview_img)
            sleep(0.03)

    # def update_preview_img(self, img_cv):
    #     if img_cv is None:
    #         return
    #     height, width = img_cv.shape[:2]
    #     scale = min(900 / width, 700 / height)
    #     resized = cv2.resize(img_cv, (int(width * scale), int(height * scale)))
    #     img_rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
    #     img_pil = Image.fromarray(img_rgb)
    #     img_tk = ImageTk.PhotoImage(img_pil)
    #     self.img_label.config(image=img_tk)
    #     self.img_label.image = img_tk

    def update_preview_img(self, img_cv):
        if img_cv is None:
            self.img_label.config(image='',bg="#8be7a3", fg="white")
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
        else: 
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

        self.update_preview_img(result_img)

    def load_from_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp")])
        if file_path:
            img = cv2.imread(file_path)
            if img is not None:
                self.current_img = img.copy()
                self.update_preview_img(img)
                self.log(f"Loaded: {os.path.basename(file_path)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = BarcodeOCRTool(root)
    root.mainloop()