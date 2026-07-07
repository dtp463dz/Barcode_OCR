import tkinter as tk
from tkinter import simpledialog, messagebox

import cv2
from PIL import Image, ImageTk

HANDLE_SIZE = 8  # vung (px tren canvas) tinh la "gan goc" de resize


class ROIEditor(tk.Toplevel):
    def __init__(self, master, image_bgr, roi_manager, on_save=None):
        super().__init__(master)
        self.title("ROI Editor - Chinh sua vung nhan dien QR")
        self.geometry("1100x750")

        self.roi_manager = roi_manager
        self.image_bgr = image_bgr
        self.on_save = on_save

        self.scale = 1.0
        self.offset = (0, 0)
        self.drag_mode = None       # "move" | "resize" | "new" | None
        self.drag_roi_id = None
        self.drag_start = None
        self.drag_orig = None
        self.new_rect_id = None

        self._build_ui()
        self._render_base_image()
        self._redraw_rois()

    # ------------------------------------------------------------------
    def _build_ui(self):
        top = tk.Frame(self)
        top.pack(fill=tk.X, padx=8, pady=6)
        tk.Label(top, text="Ve vung trong = them ROI moi (hang/cot tu tinh theo vi tri).").pack(side=tk.LEFT)
        tk.Button(top, text="Luu ROI", command=self._save, bg="#2e7d32", fg="white").pack(side=tk.RIGHT, padx=5)
        tk.Button(top, text="Dong (khong luu)", command=self.destroy).pack(side=tk.RIGHT, padx=5)

        self.canvas = tk.Canvas(self, bg="#333333")
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Button-3>", self._on_right_click)

        self.status_var = tk.StringVar(value="San sang.")
        tk.Label(self, textvariable=self.status_var, anchor="w").pack(fill=tk.X, padx=8, pady=(0, 6))

    def _render_base_image(self):
        self.update_idletasks()
        cw = max(self.canvas.winfo_width(), 900)
        ch = max(self.canvas.winfo_height(), 600)
        h, w = self.image_bgr.shape[:2]
        self.scale = min(cw / w, ch / h, 1.0) or 1.0
        disp = cv2.resize(self.image_bgr, (int(w * self.scale), int(h * self.scale)))
        rgb = cv2.cvtColor(disp, cv2.COLOR_BGR2RGB)
        self.tk_img = ImageTk.PhotoImage(Image.fromarray(rgb))
        self.canvas.delete("bg")
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img, tags="bg")
        self.canvas.config(scrollregion=(0, 0, disp.shape[1], disp.shape[0]))

    # -- chuyen doi toa do anh goc <-> canvas ---------------------------
    def _img_to_canvas(self, x, y):
        return x * self.scale, y * self.scale

    def _canvas_to_img(self, x, y):
        return int(x / self.scale), int(y / self.scale)

    # ------------------------------------------------------------------
    def _redraw_rois(self):
        self.canvas.delete("roi")
        for r in self.roi_manager.rois:
            x0, y0 = self._img_to_canvas(r["x"], r["y"])
            x1, y1 = self._img_to_canvas(r["x"] + r["width"], r["y"] + r["height"])
            color = "#42a5f5"
            self.canvas.create_rectangle(x0, y0, x1, y1, outline=color, width=2,
                                          tags=("roi", f"roi_{r['id']}"))
            self.canvas.create_text(x0 + 3, y0 - 8, anchor="w", fill=color,
                                     text=r["id"], font=("Arial", 9, "bold"),
                                     tags=("roi", f"roi_{r['id']}"))

    # ------------------------------------------------------------------
    def _roi_at(self, cx, cy):
        """Tra ve (roi_dict, mode) - mode la 'resize' neu gan goc, 'move' neu ben trong."""
        ix, iy = self._canvas_to_img(cx, cy)
        for r in reversed(self.roi_manager.rois):
            x0, y0 = r["x"], r["y"]
            x1, y1 = r["x"] + r["width"], r["y"] + r["height"]
            near_corner = (abs(ix - x1) < HANDLE_SIZE / self.scale and
                           abs(iy - y1) < HANDLE_SIZE / self.scale)
            if near_corner:
                return r, "resize"
            if x0 <= ix <= x1 and y0 <= iy <= y1:
                return r, "move"
        return None, None

    # ------------------------------------------------------------------
    def _on_press(self, event):
        roi, mode = self._roi_at(event.x, event.y)
        if roi is not None:
            self.drag_mode = mode
            self.drag_roi_id = roi["id"]
            self.drag_start = (event.x, event.y)
            self.drag_orig = dict(roi)
        else:
            # bat dau ve khung moi
            self.drag_mode = "new"
            self.drag_start = (event.x, event.y)
            self.new_rect_id = self.canvas.create_rectangle(
                event.x, event.y, event.x, event.y, outline="#ffca28", width=2, tags="new")

    def _on_drag(self, event):
        if self.drag_mode == "move" and self.drag_roi_id:
            dx = (event.x - self.drag_start[0]) / self.scale
            dy = (event.y - self.drag_start[1]) / self.scale
            r = self.roi_manager.get(self.drag_roi_id)
            r["x"] = int(self.drag_orig["x"] + dx)
            r["y"] = int(self.drag_orig["y"] + dy)
            self._redraw_rois()
        elif self.drag_mode == "resize" and self.drag_roi_id:
            ix, iy = self._canvas_to_img(event.x, event.y)
            r = self.roi_manager.get(self.drag_roi_id)
            r["width"] = max(10, int(ix - r["x"]))
            r["height"] = max(10, int(iy - r["y"]))
            self._redraw_rois()
        elif self.drag_mode == "new" and self.new_rect_id:
            self.canvas.coords(self.new_rect_id, self.drag_start[0], self.drag_start[1],
                                event.x, event.y)

    def _on_release(self, event):
        if self.drag_mode == "new" and self.new_rect_id:
            x0c, y0c = self.drag_start
            x1c, y1c = event.x, event.y
            x0c, x1c = sorted((x0c, x1c))
            y0c, y1c = sorted((y0c, y1c))
            self.canvas.delete(self.new_rect_id)
            self.new_rect_id = None
            if (x1c - x0c) > 5 and (y1c - y0c) > 5:
                ix0, iy0 = self._canvas_to_img(x0c, y0c)
                ix1, iy1 = self._canvas_to_img(x1c, y1c)
                new_id = self.roi_manager.next_free_id()
                self.roi_manager.upsert_manual(new_id, ix0, iy0, ix1 - ix0, iy1 - iy0)
                self.status_var.set(f"Da them ROI moi: {new_id}")
                self._redraw_rois()
        elif self.drag_roi_id:
            self.roi_manager._infer_grid()  # cap nhat lai hang/cot theo vi tri moi
            self.status_var.set(f"Da cap nhat ROI: {self.drag_roi_id}")

        self.drag_mode = None
        self.drag_roi_id = None

    # ------------------------------------------------------------------
    def _on_right_click(self, event):
        roi, _ = self._roi_at(event.x, event.y)
        if roi is None:
            return
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label=f"Xoa {roi['id']}", command=lambda: self._delete(roi["id"]))
        menu.add_command(label="Doi ID", command=lambda: self._rename(roi["id"]))
        menu.tk_popup(event.x_root, event.y_root)

    def _delete(self, roi_id):
        self.roi_manager.delete(roi_id)
        self._redraw_rois()
        self.status_var.set(f"Da xoa {roi_id}")

    def _rename(self, roi_id):
        new_id = simpledialog.askstring("Doi ID", f"ID moi cho '{roi_id}':", parent=self)
        if new_id:
            r = self.roi_manager.get(roi_id)
            r["id"] = new_id
            self._redraw_rois()

    # ------------------------------------------------------------------
    def _save(self):
        if self.on_save:
            self.on_save(self.roi_manager)
        messagebox.showinfo("ROI Editor", f"Da xac nhan {len(self.roi_manager.rois)} ROI.")
        self.destroy()
