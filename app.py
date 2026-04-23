import os
import subprocess
import threading
import pywinstyles
import base64
from PIL import Image

from tkinter import messagebox

import ctypes

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except:
        pass

import customtkinter as ctk
from utils import resource_path, filtrar_props

def img_to_base64(path):
    with open(path, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()

class App(ctk.CTk):

    COLOR_CONNECTED    = "#4CAF50"
    COLOR_DISCONNECTED = "#F44336"

    RISK_HIGH = {
        "🧬 FINGERPRINT",
        "🔐 Security Patch",
        "🤖 GMS/API",
        "🧬 Prop ID",
    }

    IMPORTANT_PROPS = {
        "📱 IDENTIDADE": [
            "ro.product.device",
            "ro.product.model",
            "ro.product.name"
        ],
        "🧬 FINGERPRINT": [
            "ro.build.fingerprint",
            "ro.bootimage.build.fingerprint",
            "ro.system.build.fingerprint",
            "ro.vendor.build.fingerprint",
            "ro.product.build.fingerprint",
            "ro.odm.build.fingerprint"
        ],
        "🔢 VERSIONAMENTO": [
            "ro.build.version.incremental",
            "ro.build.display.id",
            "ro.build.version.release"
        ],
        "🔐 Security Patch": [
            "ro.build.version.security_patch"
        ],
        "🧱 Base OS": [
            "ro.build.version.base_os"
        ],
        "🤖 GMS/API": [
            "ro.com.google.gmsversion",
            "ro.product.first_api_level"
        ],
        "⚙️ CPU": [
            "ro.product.cpu.abilist32",
            "ro.product.cpu.abilist64"
        ],
        "🧪 BUILD": [
            "ro.build.type"
        ],
        "🧬 Prop ID": [
            "ro.boot.vbmeta.digest"
        ],
        "🔑 Client ID": [
            "ro.com.google.clientidbase",
            "ro.com.google.clientidbase.ms",
            "ro.com.google.clientidbase.vs"
        ]
    }

    def __init__(self):
        super().__init__()

        self.largura_janela = 500
        self.altura_janela = 600

        self.title("Android SW Diff Tool")

         # Agora tentamos carregar e mostrar a LOGO
        self.logo_label = None 
        try:
            # Caminho simplificado para teste
            logo_path = "assets/logo_positivo.png"
            logo_android_path = "assets/logo_android.png"
            
            if os.path.exists(logo_path):
                logo_pil = Image.open(logo_path)
                logo_img = ctk.CTkImage(
                    light_image=logo_pil,
                    dark_image=logo_pil,
                    size=(60, 60)
                )

                self.logo_label = ctk.CTkLabel(self, image=logo_img, text="")
                self.logo_label.image = logo_img # Referência forte
                self.logo_label.place(relx=0.98, y=10, anchor="ne")            
        except Exception as e:
            pass
        

        # ── status ADB ────────────────────────────────────────────────────
        self.status_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.status_frame.pack(pady=5)

        self.status_dot = ctk.CTkLabel(self.status_frame, text="●", font=("Arial", 20))
        self.status_dot.pack(side="left", padx=5)

        self.status_text = ctk.CTkLabel(self.status_frame, text="Desconectado")
        self.status_text.pack(side="left")

        # ── barra de controles: reset + toggle tema ───────────────────────
        ctrl_frame = ctk.CTkFrame(self, fg_color="transparent")
        ctrl_frame.pack(pady=10, padx=80, fill="x")

        self.btn_reset = ctk.CTkButton(
            ctrl_frame,
            text="RESETAR",
            command=self.resetar,
            fg_color="#444444"
        )
        self.btn_reset.pack(side="left", fill="x", expand=True, padx=(0, 6))

        # ✅ ALTERAÇÃO #2: botão toggle Dark ↔ Light (sem crash)
        self._tema_atual = "Dark"
        self.btn_tema = ctk.CTkButton(
            ctrl_frame,
            text="☀ Modo Claro",
            command=self._toggle_tema,
            fg_color="#555555",
            width=120
        )
        self.btn_tema.pack(side="left")

        # ── estado interno ────────────────────────────────────────────────
        self.last_device_state    = False
        self.coletando            = False
        self.device_detected_once = False
        self.build_a_id           = ""
        self.build_b_id           = ""
        self.serial_a             = ""

        self.props_a = ""
        self.props_b = ""
        self.pkgs_a  = ""
        self.pkgs_b  = ""
        self.feats_a = ""
        self.feats_b = ""

        self.report_window = None

         # ── corpo principal ───────────────────────────────────────────────
        self.label_title = ctk.CTkLabel(
            self, text="Android SW Diff Tool",
            font=ctk.CTkFont(size=22, weight="bold")
        )

        self.label_title.pack(pady=(20, 15))

        self.label_instruction = ctk.CTkLabel(
            self,
            text="INSTRUÇÃO: Conecte o primeiro dispositivo",
            text_color=("#1A1A1A", "#FFCC00"),
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.label_instruction.pack(pady=5)

        self.btn_a = ctk.CTkButton(
            self, text="COLETAR BUILD A",
            command=lambda: self.coletar(1), height=50
        )
        self.btn_a.pack(pady=10, padx=80, fill="x")

        self.btn_b = ctk.CTkButton(
            self, text="COLETAR BUILD B",
            command=lambda: self.coletar(2),
            height=50, state="disabled", fg_color="gray"
        )
        self.btn_b.pack(pady=10, padx=80, fill="x")

        self.btn_diff = ctk.CTkButton(
            self, text="GERAR DIFERENÇA GERAL", command=self.gerar_diff,
            height=60, state="disabled", fg_color="#2E7D32",
            font=("Segoe UI", 14, "bold")
        )
        self.btn_diff.pack(pady=30, padx=80, fill="x")

        self.status_box = ctk.CTkTextbox(
            self, 
            height=100, 
            font=("Consolas", 13),
            # Tupla: (Fundo no modo Light, Fundo no modo Dark)
            fg_color=("white", "#1a1a1a"), 
            # Tupla: (Texto no modo Light, Texto no modo Dark)
            text_color=("black", "white"),
            border_width=1, 
            border_color=("#cccccc", "#333333")
        )
        self.status_box.pack(pady=10, padx=20, fill="x")

        # ✅ ALTERAÇÃO #4: footer fixo na base
        ctk.CTkLabel(
            self,
            text="Android SW Diff Tool v1.0  —  desenvolvido por Guilherme Lima",
            font=("Segoe UI", 11),
            text_color=("#333333", "#999999")
        ).pack(side="bottom", pady=(0, 8))

        # ── inicialização ─────────────────────────────────────────────────
        self.log("Aguardando conexão ADB...")
        self.check_adb_loop()

        self.update_idletasks()
        self.geometry(f"{self.largura_janela}x{self.altura_janela}")
        self.after(10, self.centralizar)

    # ✅ ALTERAÇÃO #2: troca tema sem fechar janelas nem crashar
    def _toggle_tema(self):
        if self._tema_atual == "Dark":
            novo_modo = "light"
            self._tema_atual = "Light"
            texto_botao = "🌙 Modo Escuro"
            cor_barra = "#ffffff"
        else:
            novo_modo = "dark"
            self._tema_atual = "Dark"
            texto_botao = "☀ Modo Claro"
            cor_barra = "#1a1a1a"

        # Suaviza a transição
        self.attributes("-alpha", 0.98)
        
        ctk.set_appearance_mode(novo_modo)
        self.btn_tema.configure(text=texto_botao)

        # Sincroniza a barra de título do Windows
        try:
            pywinstyles.change_header_color(self, cor_barra)
            if self.report_window and self.report_window.winfo_exists():
                pywinstyles.change_header_color(self.report_window, cor_barra)
        except:
            pass

        self.update_idletasks()
        self.update()
        self.attributes("-alpha", 1.0)

    def log(self, msg):
        self.status_box.insert("end", f"> {msg}\n")
        self.status_box.see("end")

    def rodar_adb(self, comando):
        try:
            res = subprocess.run(comando, capture_output=True, text=True, timeout=12)
            return res.stdout if res.returncode == 0 else None
        except Exception:
            return None

    def check_adb_loop(self):
        out = self.rodar_adb(["adb", "get-state"])
        current_state = True if out and "device" in out else False

        if current_state:
            if not self.device_detected_once:
                id_build = self.get_device_id()
                self.status_dot.configure(text_color=self.COLOR_CONNECTED)
                self.status_text.configure(
                    text=f"Conectado: {id_build.strip() if id_build else 'Unknown'}"
                )
                self.log(f"DEVICE DETECTADO: {id_build.strip() if id_build else 'Unknown'}")
                self.device_detected_once = True
        else:
            if self.device_detected_once:
                self.status_dot.configure(text_color=self.COLOR_DISCONNECTED)
                self.status_text.configure(text="Desconectado")
                self.log("DEVICE DESCONECTADO.\n")
                self.device_detected_once = False

        self.after(2000, self.check_adb_loop)

    def coletar(self, versao):
        if self.coletando:
            return

        self.coletando = True
        self.btn_a.configure(state="disabled")
        self.btn_b.configure(state="disabled")
        self.log(f"Coletando Build {versao}... aguarde")

        def _coleta_worker():
            display_id = self.get_device_id()
            if not display_id:
                self.after(0, lambda: messagebox.showerror("Erro", "Dispositivo não encontrado."))
                self.after(0, self._liberar_coleta_erro, versao)
                return

            props = self.rodar_adb(["adb", "shell", "getprop"])
            pkgs  = self.rodar_adb(["adb", "shell", "pm", "list", "packages"])
            feats = self.rodar_adb(["adb", "shell", "pm", "list", "features"])

            if not all([props, pkgs, feats]):
                self.after(0, lambda: messagebox.showerror(
                    "Erro de Coleta",
                    "Falha ao coletar dados do dispositivo.\n"
                    "Verifique a conexão ADB e tente novamente."
                ))
                self.after(0, self._liberar_coleta_erro, versao)
                return

            if versao == 2 and self.serial_a:
                serial_atual = (self.rodar_adb(["adb", "get-serialno"]) or "").strip()
                if serial_atual and serial_atual == self.serial_a:
                    continuar = [False]

                    def _perguntar():
                        continuar[0] = messagebox.askyesno(
                            "⚠ Atenção — Mesmo Dispositivo",
                            f"O dispositivo conectado parece ser o MESMO utilizado na coleta da Build A.\n\n"
                            f"SN: {serial_atual}\n\n"
                            f"Isso resultará em uma comparação sem diferenças (Build A vs Build A).\n\n"
                            f"Deseja continuar mesmo assim?"
                        )
                        if not continuar[0]:
                            self._liberar_coleta_erro(versao)

                    self.after(0, _perguntar)

                    import time
                    timeout = 30
                    while timeout > 0 and not continuar[0]:
                        time.sleep(0.1)
                        timeout -= 0.1
                    if not continuar[0]:
                        return

            self.after(0, lambda: self._aplicar_coleta(
                versao, display_id.strip(), props, pkgs, feats
            ))

        threading.Thread(target=_coleta_worker, daemon=True).start()

    def _liberar_coleta_erro(self, versao):
        self.coletando = False
        if versao == 1:
            self.btn_a.configure(state="normal")
        else:
            self.btn_b.configure(state="normal")

    def _aplicar_coleta(self, versao, display_id, props, pkgs, feats):
        self.log(f"Coleta Build {versao} concluída: {display_id}\n")

        if versao == 1:
            self.props_a    = props
            self.pkgs_a     = pkgs
            self.feats_a    = feats
            self.build_a_id = display_id
            self.serial_a   = (self.rodar_adb(["adb", "get-serialno"]) or "").strip()

            self.btn_a.configure(
                state="disabled",
                text=f"OK: {display_id}",
                fg_color="#333333"
            )
            self.btn_b.configure(state="normal", fg_color="#1f538d")
            self.label_instruction.configure(
                text="PASSO 2: Troque o dispositivo e Colete a B",
                text_color="#00E5FF"
            )
            messagebox.showinfo(
                "Sucesso",
                f"Build A Coletada!\nID: {display_id}\n\nAgora conecte o próximo aparelho."
            )

        else:
            self.props_b    = props
            self.pkgs_b     = pkgs
            self.feats_b    = feats
            self.build_b_id = display_id

            self.btn_b.configure(
                state="disabled",
                text=f"OK: {display_id}",
                fg_color="#333333"
            )
            self.btn_diff.configure(state="normal")
            self.label_instruction.configure(
                text="PRONTO: Clique no botão verde para ver o diff",
                text_color="#00C853"
            )

        self.coletando = False

    def gerar_diff(self):

        def get_set_from_text(texto):
            return set(l.strip() for l in texto.splitlines() if l.strip())

        pkgs_a = get_set_from_text(self.pkgs_a)
        pkgs_b = get_set_from_text(self.pkgs_b)
        feat_a = get_set_from_text(self.feats_a)
        feat_b = get_set_from_text(self.feats_b)

        prop_a = filtrar_props(self.props_a)
        prop_b = filtrar_props(self.props_b)

        data = {
            'pkgs':  {'added': sorted(pkgs_b - pkgs_a), 'removed': sorted(pkgs_a - pkgs_b)},
            'feats': {'added': sorted(feat_b - feat_a), 'removed': sorted(feat_a - feat_b)},
            'props': {}
        }

        for categoria, keys in self.IMPORTANT_PROPS.items():
            data['props'][categoria] = []
            for k in keys:
                va = prop_a.get(k, "---")
                vb = prop_b.get(k, "---")
                data['props'][categoria].append({'key': k, 'a': va, 'b': vb})

        # 🔥 novo fluxo direto
        self.gerar_html_report(data)

    def get_device_id(self):
        return self.rodar_adb(["adb", "shell", "getprop", "ro.build.display.id"])

    def resetar(self):
        self.log("Resetando estado...\n")

        if self.report_window and self.report_window.winfo_exists():
            self.report_window.destroy()
        self.report_window = None

        self.props_a = ""
        self.props_b = ""
        self.pkgs_a  = ""
        self.pkgs_b  = ""
        self.feats_a = ""
        self.feats_b = ""

        self.build_a_id = ""
        self.build_b_id = ""
        self.serial_a   = ""

        self.coletando = False

        self.btn_a.configure(
            state="normal",
            text="COLETAR BUILD A",
            fg_color=("#3a7ff6", "#1f538d")
        )
        self.btn_b.configure(
            state="disabled",
            text="COLETAR BUILD B",
            fg_color="gray"
        )
        self.btn_diff.configure(state="disabled")

        self.label_instruction.configure(
            text="INSTRUÇÃO: Conecte o primeiro dispositivo",
            text_color=("#1A1A1A", "#FFCC00")
        )

    def centralizar(self):
        largura = self.largura_janela
        altura = self.altura_janela

        tela_largura = self.winfo_screenwidth()

        x = x = int(tela_largura / 2 - largura / 2)
        y = 0

        self.geometry(f"{largura}x{altura}+{x}+{y}")

    def gerar_html_report(self, data):
        import tempfile
        import webbrowser

        def calcular_diff_props(props):
            return sum(
                1 for p in props
                if p['a'] != p['b'] and p['a'] != "---" and p['b'] != "---"
            )

        # ================= PROPERTIES =================
        props_html = ""
        total_props_diff = 0

        # DEPOIS — feature 3: ordena (com mudança primeiro), feature 2: oculta sem diff, feature 8: qtde no status
        props_items = list(data['props'].items())
        # Feature 3: grupos com mudança sobem
        props_items.sort(key=lambda item: calcular_diff_props(item[1]) == 0)

        for categoria, props in props_items:
            if not props:
                continue

            n_diff = calcular_diff_props(props)
            total_props_diff += n_diff

            # Feature 8: mostra qtde no badge
            if n_diff == 0:
                status_html = '<span class="status ok">✓ Idêntico</span>'
                # Feature 2: sem mudança → oculto por padrão
                body_class = 'block-body collapsed'
                arrow = '▶'
            else:
                status_html = f'<span class="status bad">⚠ {n_diff} mudança{"s" if n_diff > 1 else ""}</span>'
                # Feature 2: com mudança → expandido por padrão
                body_class = 'block-body'
                arrow = '▼'

            rows = ""
            for p in props:
                # Feature 1: destaca linha amarela se valor mudou
                changed = p['a'] != p['b'] and p['a'] != '---' and p['b'] != '---'
                row_class = ' class="row-changed"' if changed else ''

                status_icon = "✔" if not changed else "✖"
                status_class = "status-ok" if not changed else "status-bad"

                rows += f"""
                <tr>
                    <td class="status-cell {status_class}">{status_icon}</td>
                    <td><span class="prop-key">{p['key']}</span></td>
                    <td class="col-a"><div class="value-box">{p['a']}</div></td>
                    <td class="col-b"><div class="value-box">{p['b']}</div></td>
                </tr>
                """

            props_html += f"""
            <div class="block">
                <div class="block-header" onclick="toggleBlock(this)">
                    <div class="block-header-left">
                        <h3>{categoria} <span class="collapse-arrow">{arrow}</span></h3>
                    </div>
                    <div class="block-header-right">
                        {status_html}
                    </div>
                </div>
                <div class="{body_class}">
                    <table>
                        <thead><tr>
                            <th class="status-head">Status</th>
                            <th>Property</th>
                            <th class="col-a-head">{self.build_a_id}</th>
                            <th class="col-b-head">{self.build_b_id}</th>
                        </tr></thead>
                        <tbody>{rows}</tbody>
                    </table>
                </div>
            </div>
            """

        # ================= PACKAGES / FEATURES =================
        pkgs_added   = data['pkgs']['added']
        pkgs_removed = data['pkgs']['removed']
        feats_added  = data['feats']['added']
        feats_removed = data['feats']['removed']

        def build_dual_list(left, right, label_left, label_right):
            max_len = max(len(left), len(right), 1)
            rows = ""
            for i in range(max_len):
                l = left[i]  if i < len(left)  else ""
                r = right[i] if i < len(right) else ""
                rows += f"<tr><td>{l}</td><td>{r}</td></tr>"
            return f"""
            <table>
            <tr>
                <th>{label_left}</th>
                <th>{label_right}</th>
            </tr>
            {rows}
            </table>
            """

        pkgs_table = build_dual_list(
            pkgs_removed,
            pkgs_added,
            f"Build A  —  {self.build_a_id}",
            f"Build B  —  {self.build_b_id}"
        )

        feats_table = build_dual_list(
            [f"- {x}" for x in feats_removed],
            [f"+ {x}" for x in feats_added],
            f"Build A  —  {self.build_a_id}",
            f"Build B  —  {self.build_b_id}"
        )

        # ================= TEMPLATE =================
        template_path = resource_path("assets/templates/report_template.html")

        with open(template_path, "r", encoding="utf-8") as f:
            template = f.read()

        logo_path = img_to_base64(resource_path("assets/logo_positivo.png"))
        logo_android_path = img_to_base64(resource_path("assets/logo_android.png"))

        from datetime import datetime

        html = template
        html = html.replace("{{LOGO_PATH}}",         logo_path.replace("\\", "/"))
        html = html.replace("{{LOGO_ANDROID_PATH}}", logo_android_path.replace("\\", "/"))

        html = html.replace("{{BUILD_A}}", self.build_a_id)
        html = html.replace("{{BUILD_B}}", self.build_b_id)
        html = html.replace("{{DATE}}",    datetime.now().strftime("%d/%m/%Y %H:%M:%S"))

        html = html.replace("{{TOTAL_PROPS}}", str(total_props_diff))
        html = html.replace("{{PROPS_HTML}}",  props_html)

        html = html.replace("{{TOTAL_PKGS}}", str(len(pkgs_added) + len(pkgs_removed)))
        html = html.replace("{{PKGS_TABLE}}", pkgs_table)

        html = html.replace("{{TOTAL_FEATS}}", str(len(feats_added) + len(feats_removed)))
        html = html.replace("{{FEATS_TABLE}}", feats_table)

        # ================= OUTPUT =================
        path = tempfile.NamedTemporaryFile(delete=False, suffix=".html").name

        with open(path, "w", encoding="utf-8") as f:
            f.write(html)

        webbrowser.open(path)