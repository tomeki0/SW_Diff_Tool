import os
import subprocess
import threading
import pywinstyles
from PIL import Image

from tkinter import messagebox

import customtkinter as ctk
from report_window import ReportWindow
from utils import resource_path, filtrar_props

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

        self.largura_janela = 550
        self.altura_janela = 600  

        self.title("Android SW Diff Tool")

         # Agora tentamos carregar e mostrar a LOGO
        self.logo_label = None 
        try:
            # Caminho simplificado para teste
            logo_path = resource_path("assets/logo_positivo.png")
            
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
                            f"O dispositivo conectado ({serial_atual}) parece ser o MESMO\n"
                            f"usado para coletar a Build A.\n\n"
                            f"Isso gerará um diff vazio (A vs A).\n\n"
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
        if self.report_window and self.report_window.winfo_exists():
            self.report_window.focus()
            return

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

        self.report_window = ReportWindow(data, self.build_a_id, self.build_b_id, self)

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
        tela_altura = self.winfo_screenheight()

        x = int(tela_largura / 2 - largura / 2)
        y = int(tela_altura / 2 - altura / 2)

        self.geometry(f"{largura}x{altura}+{x}+{y}")