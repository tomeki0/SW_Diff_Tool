import customtkinter as ctk
from tkinter import ttk

COL_BUILD_A = "#1565C0"   # azul
COL_BUILD_B = "#6A1B9A"   # roxo

class ReportWindow(ctk.CTkToplevel):
    def __init__(self, data, build_a_name, build_b_name, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.title("Dashboard de Diferenças Android")

        self.geometry("1100x700")
        self.minsize(900, 600)
        self.state("normal")

        self.lift()
        self.attributes("-topmost", True)
        self.after(100, lambda: self.attributes("-topmost", False))

        self.after(50, self._centralizar)

        self.build_a = build_a_name
        self.build_b = build_b_name

        self.export_bar = ctk.CTkFrame(self, fg_color="transparent")
        self.export_bar.pack(padx=10, pady=(8, 0), fill="x")

        ctk.CTkButton(
            self.export_bar,
            text="📄 Exportar HTML",
            command=self._exportar_html,
            width=140,
            height=30,
            fg_color="#1565C0",
            font=("Segoe UI", 12)
        ).pack(side="right", padx=(4, 0))

        ctk.CTkButton(
            self.export_bar,
            text="📋 Exportar JSON",
            command=lambda: self._exportar_json(data),
            width=140,
            height=30,
            fg_color="#4A148C",
            font=("Segoe UI", 12)
        ).pack(side="right", padx=(4, 0))

        self._data = data

        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(padx=10, pady=(6, 10), fill="both", expand=True)

        self.tab_props = self.tabview.add("📊 Propriedades (Props)")
        self.tab_pkgs  = self.tabview.add("📦 Pacotes (Packages)")
        self.tab_feats = self.tabview.add("🛠 Recursos (Features)")

        self.setup_properties_tab(data['props'])
        self.setup_diff_tab(self.tab_pkgs,  data['pkgs'],  "PACOTES")
        self.setup_diff_tab(self.tab_feats, data['feats'], "RECURSOS")

    def _centralizar(self):
        self.update_idletasks()
        largura = self.winfo_width()
        altura  = self.winfo_height()
        x = (self.winfo_screenwidth()  // 2) - (largura // 2)
        y = (self.winfo_screenheight() // 2) - (altura  // 2)
        self.geometry(f"+{x}+{y}")

    def setup_properties_tab(self, prop_data):
        RISK_HIGH = {
            "🧬 FINGERPRINT",
            "🔐 Security Patch",
            "🤖 GMS/API",
            "🧬 Prop ID",
        }

        container = ctk.CTkScrollableFrame(self.tab_props)
        container.pack(fill="both", expand=True, padx=10, pady=10)

        style = ttk.Style()
        style.theme_use("default")

        style.configure("Treeview",
                        background="#1e1e1e",
                        foreground="white",
                        fieldbackground="#1e1e1e",
                        rowheight=80,
                        font=("Consolas", 14))

        style.configure("Treeview.Heading",
                        font=("Segoe UI", 13, "bold"))

        def wrap_text(text, max_len=60):
            if not text:
                return text
            return "\n".join([text[i:i+max_len] for i in range(0, len(text), max_len)])

        all_trees = []

        for categoria, props in prop_data.items():
            if not props:
                continue

            n_diff = sum(
                1 for p in props
                if p['a'] != p['b'] and p['a'] != "---" and p['b'] != "---"
            )

            is_risk = categoria in RISK_HIGH
            if n_diff > 0 and is_risk:
                label_suffix = f"   🔴 RISCO ALTO — {n_diff} diferença(s)"
                label_color  = "#F44336"
            elif n_diff > 0:
                label_suffix = f"   ⚠  {n_diff} diferença(s)"
                label_color  = "#FF9800"
            else:
                label_suffix = "   ✓ Idêntico"
                label_color  = "#4CAF50"

            header_frame = ctk.CTkFrame(container, fg_color="transparent")
            header_frame.pack(anchor="w", fill="x", pady=(20, 0))

            ctk.CTkLabel(
                header_frame,
                text=categoria + label_suffix,
                font=("Segoe UI", 16, "bold"),
                text_color=label_color
            ).pack(anchor="w", side="left")

            # ✅ ALTERAÇÃO #6: barrinhas azul/roxo — neutras, só para diferenciação
            color_bar_frame = ctk.CTkFrame(container, fg_color="transparent")
            color_bar_frame.pack(fill="x", pady=(4, 0))

            ctk.CTkLabel(color_bar_frame, text="", width=250).pack(side="left")

            ctk.CTkFrame(color_bar_frame, height=4,
                         fg_color=COL_BUILD_A, corner_radius=2).pack(
                side="left", fill="x", expand=True, padx=(2, 2))

            ctk.CTkFrame(color_bar_frame, height=4,
                         fg_color=COL_BUILD_B, corner_radius=2).pack(
                side="left", fill="x", expand=True, padx=(2, 0))

            tree = ttk.Treeview(container,
                                columns=("prop", "build_a", "build_b"),
                                show="headings",
                                height=min(len(props), 6))

            all_trees.append(tree)
            tree.cell_highlight = None

            # ✅ ALTERAÇÃO #6: ícones 🔵 / 🟣 nos headings — neutros
            tree.heading("prop",    text="Properties")
            tree.heading("build_a", text=f"🔵  {self.build_a}")
            tree.heading("build_b", text=f"🟣  {self.build_b}")

            tree.column("prop",    width=250)
            tree.column("build_a", width=400)
            tree.column("build_b", width=400)

            for i, p in enumerate(props):
                va, vb = p['a'], p['b']
                is_diff = va != vb and va != "---" and vb != "---"

                if is_diff:
                    tag = "diff"
                else:
                    tag = "even" if i % 2 == 0 else "odd"

                tree.insert("", "end",
                            values=(p['key'], wrap_text(va), wrap_text(vb)),
                            tags=(tag,))

            tree.tag_configure("even", background="#2a2a2a")
            tree.tag_configure("odd",  background="#1f1f1f")
            tree.tag_configure("diff", background="#3a1a00", foreground="#FFB74D")

            tree.configure(selectmode="browse")
            tree.selected_cell = None

            def on_click(event, tree=tree):
                row = tree.identify_row(event.y)
                col = tree.identify_column(event.x)

                if not row:
                    return

                for t in all_trees:
                    t.selection_remove(t.selection())
                    for item in t.get_children():
                        values = list(t.item(item, "values"))
                        values = [v.replace("[ ", "").replace(" ]", "") for v in values]
                        t.item(item, values=values)

                tree.selection_set(row)

                if not col:
                    return

                values = list(tree.item(row, "values"))
                col_index = int(col.replace("#", "")) - 1
                values[col_index] = f"[ {values[col_index]} ]"
                tree.item(row, values=values)
                tree.selected_cell = (row, col)

            tree.bind("<Button-1>", on_click)

            def copiar_duplo_click(event, tree=tree):
                row = tree.identify_row(event.y)
                col = tree.identify_column(event.x)

                if not row or not col:
                    return

                values = tree.item(row, "values")
                col_index = int(col.replace("#", "")) - 1

                if 0 <= col_index < len(values):
                    texto = values[col_index]
                    self.clipboard_clear()
                    self.clipboard_append(texto)
                    self.mostrar_toast("📋 Célula Copiada!")

            tree.bind("<Double-1>", copiar_duplo_click)
            tree.pack(fill="x", pady=5)

    def setup_diff_tab(self, tab, diff_data, tipo):

        has_diff = bool(diff_data['added'] or diff_data['removed'])

        if has_diff:
            color_a = "#F44336"
            color_b = "#4CAF50"
        else:
            color_a = "white"
            color_b = "white"

        master = ctk.CTkFrame(tab, fg_color="transparent")
        master.pack(fill="both", expand=True, padx=10, pady=10)

        f_a = ctk.CTkFrame(master, border_width=2, border_color=color_a)
        f_a.pack(side="left", fill="both", expand=True, padx=5)

        ctk.CTkLabel(
            f_a,
            text=f"EXCLUSIVO DA BUILD A\n({self.build_a})",
            text_color=color_a,
            font=("Segoe UI", 13, "bold")
        ).pack(pady=10)

        txt_a = ctk.CTkTextbox(f_a, font=("Consolas", 13), fg_color="#1e1e1e")
        txt_a.pack(fill="both", expand=True, padx=10, pady=10)

        content_a = "\n".join([f"[-] {x}" for x in diff_data['removed']])
        txt_a.insert("0.0", content_a if content_a else "Sem itens exclusivos da Build A")
        txt_a.configure(state="disabled")

        f_b = ctk.CTkFrame(master, border_width=2, border_color=color_b)
        f_b.pack(side="right", fill="both", expand=True, padx=5)

        ctk.CTkLabel(
            f_b,
            text=f"EXCLUSIVO DA BUILD B\n({self.build_b})",
            text_color=color_b,
            font=("Segoe UI", 13, "bold")
        ).pack(pady=10)

        txt_b = ctk.CTkTextbox(f_b, font=("Consolas", 13), fg_color="#1e1e1e")
        txt_b.pack(fill="both", expand=True, padx=10, pady=10)

        content_b = "\n".join([f"[+] {x}" for x in diff_data['added']])
        txt_b.insert("0.0", content_b if content_b else "Sem itens exclusivos da Build B")
        txt_b.configure(state="disabled")

    def mostrar_toast(self, msg):
        toast = ctk.CTkLabel(
            self,
            text=msg,
            fg_color="#333333",
            corner_radius=8,
            padx=10,
            pady=5
        )
        toast.place(relx=0.5, rely=0.9, anchor="center")
        self.after(1500, toast.destroy)

    def _exportar_html(self):
        from tkinter import filedialog
        import datetime

        data = self._data
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"diff_{self.build_a}_vs_{self.build_b}_{ts}.html"

        path = filedialog.asksaveasfilename(
            defaultextension=".html",
            filetypes=[("HTML", "*.html")],
            initialfile=default_name,
            title="Salvar relatório HTML"
        )
        if not path:
            return

        rows_props = ""
        for categoria, props in data['props'].items():
            for p in props:
                bg = "#3a1a00" if p['a'] != p['b'] and p['a'] != "---" else "#1e1e1e"
                fg = "#FFB74D" if p['a'] != p['b'] and p['a'] != "---" else "#ffffff"
                rows_props += (
                    f'<tr style="background:{bg};color:{fg}">'
                    f'<td>{categoria}</td>'
                    f'<td style="font-family:monospace">{p["key"]}</td>'
                    f'<td style="font-family:monospace">{p["a"]}</td>'
                    f'<td style="font-family:monospace">{p["b"]}</td>'
                    f'</tr>\n'
                )

        pkgs_removed  = "\n".join(f"<li>[-] {x}</li>" for x in data['pkgs']['removed'])
        pkgs_added    = "\n".join(f"<li>[+] {x}</li>" for x in data['pkgs']['added'])
        feats_removed = "\n".join(f"<li>[-] {x}</li>" for x in data['feats']['removed'])
        feats_added   = "\n".join(f"<li>[+] {x}</li>" for x in data['feats']['added'])

        html = f"""<!DOCTYPE html>
            <html lang="pt-BR">
            <head>
            <meta charset="UTF-8">
            <title>Android Diff — {self.build_a} vs {self.build_b}</title>
            <style>
            body {{ background:#121212; color:#fff; font-family:Segoe UI,sans-serif; padding:24px; }}
            h1 {{ color:#00E5FF; }} h2 {{ color:#90CAF9; margin-top:32px; }}
            table {{ width:100%; border-collapse:collapse; margin-top:12px; }}
            th {{ background:#1f538d; padding:8px; text-align:left; font-size:13px; }}
            td {{ padding:8px; font-size:12px; border-bottom:1px solid #333; word-break:break-all; }}
            .two-col {{ display:flex; gap:24px; margin-top:12px; }}
            .panel {{ flex:1; background:#1e1e1e; border-radius:8px; padding:16px; }}
            .panel.a {{ border:2px solid #F44336; }} .panel.b {{ border:2px solid #4CAF50; }}
            .panel h3.a {{ color:#F44336; }} .panel h3.b {{ color:#4CAF50; }}
            ul {{ padding-left:20px; font-family:monospace; font-size:12px; line-height:1.8; }}
            </style>
            </head>
            <body>
            <h1>📱 Android SW Diff Report</h1>
            <p>Build A: <strong>{self.build_a}</strong> &nbsp;|&nbsp; Build B: <strong>{self.build_b}</strong></p>
            <p>Gerado em: {datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")}</p>

            <h2>📊 Propriedades</h2>
            <table>
            <tr>
                <th>Categoria</th><th>Property</th>
                <th>🔵 Build A — {self.build_a}</th>
                <th>🟣 Build B — {self.build_b}</th>
            </tr>
            {rows_props}
            </table>

            <h2>📦 Pacotes</h2>
            <div class="two-col">
            <div class="panel a"><h3 class="a">Exclusivo Build A (removidos)</h3><ul>{pkgs_removed or "<li>Nenhum</li>"}</ul></div>
            <div class="panel b"><h3 class="b">Exclusivo Build B (adicionados)</h3><ul>{pkgs_added  or "<li>Nenhum</li>"}</ul></div>
            </div>

            <h2>🛠 Features</h2>
            <div class="two-col">
            <div class="panel a"><h3 class="a">Exclusivo Build A (removidas)</h3><ul>{feats_removed or "<li>Nenhuma</li>"}</ul></div>
            <div class="panel b"><h3 class="b">Exclusivo Build B (adicionadas)</h3><ul>{feats_added  or "<li>Nenhuma</li>"}</ul></div>
            </div>
            </body></html>"""

        with open(path, "w", encoding="utf-8") as f:
            f.write(html)

        self.mostrar_toast("✅ HTML salvo!")

    def _exportar_json(self, data):
        import json
        import datetime
        from tkinter import filedialog

        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"diff_{self.build_a}_vs_{self.build_b}_{ts}.json"

        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
            initialfile=default_name,
            title="Salvar relatório JSON"
        )
        if not path:
            return

        payload = {
            "build_a":   self.build_a,
            "build_b":   self.build_b,
            "timestamp": datetime.datetime.now().isoformat(),
            "props":     data['props'],
            "packages":  data['pkgs'],
            "features":  data['feats'],
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        self.mostrar_toast("✅ JSON salvo!")