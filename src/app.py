import presets

from adb import (
    get_device_id,
    is_device_connected,
    get_serial,
    coletar_dados
)

from diff_engine import (
    is_changed,
    process_prop_value,
    calcular_diff_props,
    parse_packages_with_path
)

from report import gerar_html_report

import os
import threading
import pywinstyles
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
        self.apk_info_a = {}
        self.apk_info_b = {}

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

       # ── BUILD A ──────────────────────────────────────────────────────
        row_a = ctk.CTkFrame(self, fg_color="transparent")
        row_a.pack(pady=(10, 4), padx=80, fill="x")

        self.btn_a = ctk.CTkButton(
            row_a, text="COLETAR BUILD A",          # ← pai é row_a, não self
            command=lambda: self.coletar(1), height=50
        )
        self.btn_a.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.btn_preset_a = ctk.CTkButton(
            row_a, text="💾",                        # ← pai é row_a
            command=lambda: self._carregar_preset_como(1),
            height=50, width=46,
            fg_color="#2a2a2a",
            font=("Segoe UI", 18)
        )
        self.btn_preset_a.pack(side="left")

        # ── BUILD B ──────────────────────────────────────────────────────
        row_b = ctk.CTkFrame(self, fg_color="transparent")
        row_b.pack(pady=(4, 10), padx=80, fill="x")

        self.btn_b = ctk.CTkButton(
            row_b, text="COLETAR BUILD B",          # ← pai é row_b, não self
            command=lambda: self.coletar(2),
            height=50, state="disabled", fg_color="gray"
        )
        self.btn_b.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.btn_preset_b = ctk.CTkButton(
            row_b, text="💾",                        # ← pai é row_b
            command=lambda: self._carregar_preset_como(2),
            height=50, width=46,
            fg_color="#2a2a2a",
            font=("Segoe UI", 18),
            state="disabled"
        )
        self.btn_preset_b.pack(side="left")

        self.btn_diff = ctk.CTkButton(
            self, text="GERAR DIFERENÇA GERAL", command=self.gerar_diff,
            height=60, state="disabled", fg_color="#2E7D32",
            font=("Segoe UI", 14, "bold")
        )
        self.btn_diff.pack(pady=30, padx=80, fill="x")

        self.status_box = ctk.CTkTextbox(
            self, 
            height=100, 
            font=("Consolas", 12),
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
        self.log("Aguardando conexão ADB...", "info")
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
        def _reconfigurar_tags_log(self):
            is_dark = self._tema_atual == "Dark"
            mapa = {
                "tag_info":     "#a0a0b8" if is_dark else "#4b5563",
                "tag_ok":       "#4ade80" if is_dark else "#16a34a",
                "tag_erro":     "#f87171" if is_dark else "#dc2626",
                "tag_aviso":    "#fbbf24" if is_dark else "#d97706",
                "tag_destaque": "#c084fc" if is_dark else "#7c3aed",
                "tag_device":   "#38bdf8" if is_dark else "#0369a1",
            }
            for tag, cor in mapa.items():
                self.status_box.tag_config(tag, foreground=cor)
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
        self._reconfigurar_tags_log() 

    def log(self, msg: str, tipo: str = "info"):
        """
        tipo: 'info' | 'ok' | 'erro' | 'aviso' | 'destaque'
        """
        icons = {
            "info":     ">> ",
            "ok":       "[OK] ",
            "erro":     "[ERRO] ",
            "aviso":    "[!] ",
            "destaque": "*** ",
            "device":   "[DEV] ",
        }
        cores_dark = {
            "info":     "#a0a0b8",
            "ok":       "#4ade80",
            "erro":     "#f87171",
            "aviso":    "#fbbf24",
            "destaque": "#c084fc",
            "device":   "#38bdf8",
        }
        cores_light = {
            "info":     "#4b5563",
            "ok":       "#16a34a",
            "erro":     "#dc2626",
            "aviso":    "#d97706",
            "destaque": "#7c3aed",
            "device":   "#0369a1",
        }

        prefixo = icons.get(tipo, "➡️ ")
        linha = f"{prefixo}{msg}\n"

        tag = f"tag_{tipo}"
        cor = cores_dark.get(tipo, "#a0a0b8")

        self.status_box.insert("end", linha, tag)
        self.status_box.tag_config(tag, foreground=cor)
        self.status_box.see("end")

    def check_adb_loop(self):
        current_state = is_device_connected()

        if current_state:
            if not self.device_detected_once:
                id_build = (get_device_id() or "").strip()
                self.status_dot.configure(text_color=self.COLOR_CONNECTED)
                self.status_text.configure(
                    text=f"Conectado: {id_build or 'Unknown'}"
                )
                self.log(f"Dispositivo conectado: {id_build.strip() if id_build else 'Unknown'}", "device")
                self.device_detected_once = True
        else:
            if self.device_detected_once:
                self.status_dot.configure(text_color=self.COLOR_DISCONNECTED)
                self.status_text.configure(text="Desconectado")
                self.log("Dispositivo desconectado.", "aviso")
                self.device_detected_once = False

        self.after(2000, self.check_adb_loop)

    def coletar(self, versao):
        if self.coletando:
            return

        self.coletando = True
        self.btn_a.configure(state="disabled")
        self.btn_b.configure(state="disabled")
        self.log(f"Iniciando coleta da Build {versao}...", "info")

        def _coleta_worker():
            display_id = (get_device_id() or "").strip()
            if not display_id:
                self.after(0, lambda: messagebox.showerror("Erro", "Dispositivo não encontrado."))
                self.after(0, self._liberar_coleta_erro, versao)
                return

            props, pkgs, feats = coletar_dados()

            if not all([props, pkgs, feats]):
                self.after(0, lambda: messagebox.showerror(
                    "Erro de Coleta",
                    "Falha ao coletar dados do dispositivo.\n"
                    "Verifique a conexão ADB e tente novamente."
                ))
                self.after(0, self._liberar_coleta_erro, versao)
                return

            if versao == 2 and self.serial_a:
                serial_atual = get_serial()
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
        self.log(f"Build {versao} coletada com sucesso: {display_id}", "ok")

        if versao == 1:
            self.props_a    = props
            self.pkgs_a     = pkgs
            self.feats_a    = feats
            self.apk_info_a = presets.extrair_info_apk(pkgs)
            self.build_a_id = display_id
            self.serial_a   = get_serial() or ""

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
            self.apk_info_b = presets.extrair_info_apk(pkgs)
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
        print("LEN PKGS A:", len(self.pkgs_a.splitlines()))
        

    def gerar_diff(self):

        def get_set_from_text(texto):
            result = set()

            for line in texto.splitlines():
                line = line.strip()

                if not line:
                    continue

                # 🔥 NOVO: extrair só o package
                if "=" in line:
                    try:
                        pkg = line.split("=")[-1]
                        result.add(pkg)
                    except:
                        continue
                else:
                    result.add(line)

            return result

        pkgs_path_a = parse_packages_with_path(self.pkgs_a) if isinstance(self.pkgs_a, str) else {}
        pkgs_path_b = parse_packages_with_path(self.pkgs_b) if isinstance(self.pkgs_b, str) else {}

        pkgs_a = set(pkgs_path_a.keys())
        pkgs_b = set(pkgs_path_b.keys())
        
        feat_a = get_set_from_text(self.feats_a) if isinstance(self.feats_a, str) else set()
        feat_b = get_set_from_text(self.feats_b) if isinstance(self.feats_b, str) else set()

        # suporta tanto dict (preset) quanto string raw (ADB)
        prop_a = filtrar_props(self.props_a)
        prop_b = filtrar_props(self.props_b)

        data = {
            'pkgs':  {'added': sorted(pkgs_b - pkgs_a), 'removed': sorted(pkgs_a - pkgs_b)},
            'feats': {'added': sorted(feat_b - feat_a), 'removed': sorted(feat_a - feat_b)},
            'props': {},
            'apk_info_a': self.apk_info_a,
            'apk_info_b': self.apk_info_b,
            'raw_pkgs_a': self.pkgs_a,
            'raw_pkgs_b': self.pkgs_b,
        }

        for categoria, keys in self.IMPORTANT_PROPS.items():
            data['props'][categoria] = []
            for k in keys:
                va = prop_a.get(k, "---")
                vb = prop_b.get(k, "---")
                data['props'][categoria].append({'key': k, 'a': va, 'b': vb})

        # 🔥 novo fluxo direto
        gerar_html_report(
            data,
            self.build_a_id,
            self.build_b_id,
            self.log
        )

    def resetar(self):
        self.log("Estado resetado.", "aviso")

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
        
    def _pedir_nome_preset(self, versao, props_raw, build_id):
        """Abre um dialog simples para nomear e salvar o preset."""
        dialog = ctk.CTkInputDialog(
            text=f"Nome para salvar o preset da Build {versao}:\n(ex: MR1 - Display ID Projeto X)",
            title="Salvar Preset"
        )
        nome = dialog.get_input()
        if nome and nome.strip():
            props_filtradas = filtrar_props(props_raw)
            apk_info = presets.extrair_info_apk(self.pkgs_a if versao == 1 else self.pkgs_b)

            path = presets.salvar(
                nome.strip(),
                props_filtradas,
                build_id,
                packages=self.pkgs_a if versao == 1 else self.pkgs_b,
                features=self.feats_a if versao == 1 else self.feats_b,
                apk_info=apk_info
            )
            messagebox.showinfo("Preset salvo", f"Salvo em:\n{path}")

    def _carregar_preset_como(self, versao):
        lista_presets = presets.listar()

        win = ctk.CTkToplevel(self)
        win.title("Presets")
        win.geometry("520x460")
        win.grab_set()

        # ── botão salvar o build atual (se já foi coletado) ──────────
        props_atual = self.props_a if versao == 1 else self.props_b
        build_atual = self.build_a_id if versao == 1 else self.build_b_id

        if props_atual and build_atual:
            def _salvar_atual():
                dialog = ctk.CTkInputDialog(
                    text=f"Nome para o preset da Build {versao}:\n(ex: MR1 - Projeto X)",
                    title="Salvar Preset"
                )
                nome = dialog.get_input()
                if nome and nome.strip():
                    props_f = props_atual if isinstance(props_atual, dict) else filtrar_props(props_atual)
                    apk_info = presets.extrair_info_apk(
                        self.pkgs_a if versao == 1 else self.pkgs_b
                    )

                    path = presets.salvar(
                        nome.strip(),
                        props_f,
                        build_atual,
                        packages=self.pkgs_a if versao == 1 else self.pkgs_b,
                        features=self.feats_a if versao == 1 else self.feats_b,
                        apk_info=apk_info
                    )
                    
                    messagebox.showinfo("Salvo!", f"Preset salvo em:\n{path}")
                    win.destroy()
                    # reabre pra mostrar o novo preset na lista
                    self.after(100, lambda: self._carregar_preset_como(versao))

            ctk.CTkButton(
                win,
                text=f"💾  Salvar  [{build_atual}]  como preset",
                command=_salvar_atual,
                fg_color="#1e4d2b",
                hover_color="#2a6b3c",
                height=38,
                font=("Segoe UI", 12, "bold")
            ).pack(fill="x", padx=16, pady=(14, 4))

            ctk.CTkLabel(
                win, text="── ou carregar um preset existente ──",
                font=("Segoe UI", 10), text_color="gray"
            ).pack(pady=(0, 4))
        else:
            ctk.CTkLabel(
                win, text="Carregar preset salvo",
                font=("Segoe UI", 13, "bold")
            ).pack(pady=(16, 6))

        # ── lista de presets ─────────────────────────────────────────
        if not lista_presets:
            ctk.CTkLabel(win, text="Nenhum preset salvo ainda.",
                        text_color="gray").pack(pady=20)
        else:
            frame = ctk.CTkScrollableFrame(win, height=260)
            frame.pack(fill="both", expand=True, padx=16, pady=4)

            def selecionar(preset):
                win.destroy()
                self._aplicar_preset(versao, preset)

            for p in lista_presets:
                data_fmt = p.get("data", "")[:16].replace("T", " ")

                # ── linha por preset ─────────────────────────────────────────
                row = ctk.CTkFrame(frame, fg_color="transparent")
                row.pack(fill="x", pady=3)

                btn = ctk.CTkButton(
                    row,
                    text=f"  {p['nome']}\n  {p['build_id']}  •  {data_fmt}",
                    anchor="w",
                    command=lambda p=p: selecionar(p),
                    fg_color="transparent",
                    border_width=1,
                    text_color=("black", "white"),
                    hover_color=("#e0e0e0", "#2a2a2a"),
                    height=52
                )
                btn.pack(side="left", fill="x", expand=True, padx=(0, 4))

                def _excluir(p=p, r=row):
                    confirmar = messagebox.askyesno(
                        "Excluir Preset",
                        f"Excluir '{p['nome']}'?\n{p['build_id']}"
                    )
                    if confirmar:
                        try:
                            presets.deletar(p["_file"])
                        except Exception as e:
                            messagebox.showerror("Erro", f"Não foi possível excluir:\n{e}")
                            return
                        r.destroy()  # remove a linha da UI sem fechar a janela
                
                # ✏ EDITAR
                def _editar(p=p):
                    dialog = ctk.CTkInputDialog(
                        text="Novo nome do preset:",
                        title="Renomear Preset"
                    )
                    novo_nome = dialog.get_input()

                    if novo_nome and novo_nome.strip():
                        try:
                            presets.renomear(p["_file"], novo_nome.strip())
                            messagebox.showinfo("Sucesso", "Preset renomeado!")
                            win.destroy()
                            self.after(100, lambda: self._carregar_preset_como(versao))
                        except Exception as e:
                            messagebox.showerror("Erro", str(e))


                ctk.CTkButton(
                    row,
                    text="✏",
                    command=_editar,
                    width=40,
                    height=52,
                    fg_color="#1a3a5a",
                    hover_color="#205080",
                    font=("Segoe UI", 16)
                ).pack(side="left")

                ctk.CTkButton(
                    row,
                    text="🗑",
                    command=_excluir,
                    width=40,
                    height=52,
                    fg_color="#5a1a1a",
                    hover_color="#7f2020",
                    font=("Segoe UI", 16)
                ).pack(side="left")

        ctk.CTkButton(
            win,
            text="📁 Abrir pasta de presets",
            command=lambda: (
                presets.PRESETS_DIR.mkdir(parents=True, exist_ok=True),
                os.startfile(str(presets.PRESETS_DIR))
            ),
            fg_color="#444",
            height=32
        ).pack(pady=8)
        
    def _aplicar_preset(self, versao, preset):
        """Simula uma coleta usando dados salvos do preset."""
        build_id = preset["build_id"]
        # Reconstrói props_raw como texto no formato getprop
        # (ou guarda direto como dict — ajusta filtrar_props pra aceitar dict)
        props_dict = preset["props"]

        if versao == 1:
            self.props_a    = props_dict   # agora é dict direto
            self.pkgs_a = preset.get("packages", "")
            self.feats_a = preset.get("features", "")
            self.apk_info_a = preset.get("apk_info", {})
            self.build_a_id = build_id
            self.serial_a   = ""
            self.btn_a.configure(state="disabled", text=f"[PRESET] {build_id}", fg_color="#333333")
            self.btn_preset_b.configure(state="normal")
            self.btn_b.configure(state="normal", fg_color="#1f538d")
            self.label_instruction.configure(
                text="PASSO 2: Conecte o aparelho B ou use um preset",
                text_color="#00E5FF"
            )
            messagebox.showinfo("Preset carregado", f"Build A: {build_id}")
        else:
            self.props_b    = props_dict
            self.pkgs_b = preset.get("packages", "")
            self.feats_b = preset.get("features", "")
            self.apk_info_b = preset.get("apk_info", {})
            self.build_b_id = build_id
            self.btn_b.configure(state="disabled", text=f"[PRESET] {build_id}", fg_color="#333333")
            self.btn_diff.configure(state="normal")
            self.label_instruction.configure(
                text="PRONTO: Clique no botão verde para ver o diff",
                text_color="#00C853"
            )