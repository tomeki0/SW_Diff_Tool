import sys, os, re
from pathlib import Path
import customtkinter as ctk

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        base = sys._MEIPASS
    else:
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    return os.path.join(base, relative_path)

def filtrar_props(texto):
    if isinstance(texto, dict):
        return texto

    d = {}
    for line in texto.splitlines():
        m = re.match(r'^\[(.+?)\]: \[(.*)?\]$', line.strip())
        if m:
            k, v = m.group(1), m.group(2)
            d[k] = v
    return d

def img_to_base64(path):
    import base64
    with open(path, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()
    
class Tooltip:
    active_tooltip = None

    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        self.after_id = None

        widget.bind("<Enter>", self.schedule_show)
        widget.bind("<Leave>", self.hide)
        widget.bind("<ButtonPress>", self.hide)

    def schedule_show(self, event=None):
        # 🔥 cancela qualquer tentativa anterior
        self.cancel_schedule()

        # delay de 200ms (ajuda MUITO)
        self.after_id = self.widget.after(200, self.show)

    def cancel_schedule(self):
        if self.after_id:
            try:
                self.widget.after_cancel(self.after_id)
            except:
                pass
            self.after_id = None

    def show(self):
        # se saiu antes do delay, não mostra
        if not self.widget.winfo_exists():
            return

        # 🔥 mata qualquer tooltip anterior
        if Tooltip.active_tooltip:
            Tooltip.active_tooltip._force_destroy()

        x = self.widget.winfo_rootx() + 15
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5

        parent = self.widget.winfo_toplevel()
        self.tipwindow = tw = ctk.CTkToplevel(parent)
        Tooltip.active_tooltip = self

        tw.wm_overrideredirect(True)
        tw.transient(parent)
        tw.wm_geometry(f"+{x}+{y}")

        label = ctk.CTkLabel(
            tw,
            text=self.text,
            fg_color=("#eeeeee", "#2a2a2a"),
            text_color=("black", "white"),
            corner_radius=6,
            padx=8,
            pady=4
        )
        label.pack()

    def hide(self, event=None):
        self.cancel_schedule()
        self._force_destroy()

    def _force_destroy(self):
        if self.tipwindow:
            try:
                self.tipwindow.destroy()
            except:
                pass
            self.tipwindow = None

        if Tooltip.active_tooltip == self:
            Tooltip.active_tooltip = None
            
    def get_base_dir():
        return Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))