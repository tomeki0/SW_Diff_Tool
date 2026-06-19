import "./style.css";
import { Adb } from "@yume-chan/adb";
import {
  isSupported,
  connect,
  collectBuild,
  close,
  type CollectedBuild,
} from "./adb";

// ── estado ──────────────────────────────────────────────────────────────────
interface State {
  adb: Adb | null;
  buildA: CollectedBuild | null;
  buildB: CollectedBuild | null;
  lastReportHtml: string | null;
  presetTarget: "A" | "B";
}

const state: State = {
  adb: null,
  buildA: null,
  buildB: null,
  lastReportHtml: null,
  presetTarget: "A",
};

// ── helpers de DOM ────────────────────────────────────────────────────────────
const $ = <T extends HTMLElement = HTMLElement>(id: string) =>
  document.getElementById(id) as T;

const els = {
  statusDot: $("statusDot"),
  statusText: $("statusText"),
  instruction: $("instruction"),
  btnConnect: $<HTMLButtonElement>("btnConnect"),
  btnCollectA: $<HTMLButtonElement>("btnCollectA"),
  btnCollectB: $<HTMLButtonElement>("btnCollectB"),
  btnPresetA: $<HTMLButtonElement>("btnPresetA"),
  btnPresetB: $<HTMLButtonElement>("btnPresetB"),
  btnGenerate: $<HTMLButtonElement>("btnGenerate"),
  btnDownload: $<HTMLButtonElement>("btnDownload"),
  btnReset: $<HTMLButtonElement>("btnReset"),
  btnManual: $<HTMLButtonElement>("btnManual"),
  log: $("log"),
  report: $<HTMLIFrameElement>("report"),
  unsupported: $("unsupported"),
  manualPanel: $<HTMLDetailsElement>("manualPanel"),
  presetDialog: $<HTMLDialogElement>("presetDialog"),
  presetList: $("presetList"),
  presetName: $<HTMLInputElement>("presetName"),
  presetTitle: $("presetTitle"),
  btnPresetSave: $<HTMLButtonElement>("btnPresetSave"),
};

function log(msg: string, kind: "info" | "ok" | "err" | "warn" = "info") {
  const line = document.createElement("span");
  line.className = kind;
  line.textContent = `${msg}\n`;
  els.log.appendChild(line);
  els.log.scrollTop = els.log.scrollHeight;
}

function setConnected(buildId: string | null) {
  if (buildId) {
    els.statusDot.className = "dot on";
    els.statusText.textContent = `Conectado: ${buildId || "Unknown"}`;
  } else {
    els.statusDot.className = "dot off";
    els.statusText.textContent = "Desconectado";
  }
}

function refreshButtons() {
  els.btnCollectA.disabled = !state.adb && !manualMode;
  els.btnCollectB.disabled = (!state.adb && !manualMode) || !state.buildA;
  els.btnGenerate.disabled = !(state.buildA && state.buildB);
  els.btnDownload.disabled = !state.lastReportHtml;

  if (state.buildA) {
    els.btnCollectA.textContent = `OK: ${state.buildA.build_id}`;
  }
  if (state.buildB) {
    els.btnCollectB.textContent = `OK: ${state.buildB.build_id}`;
  }

  if (!state.buildA) {
    els.instruction.textContent = "Conecte o primeiro dispositivo e colete a Build A";
  } else if (!state.buildB) {
    els.instruction.textContent = "Troque o dispositivo (ou use preset) e colete a Build B";
  } else {
    els.instruction.textContent = "Pronto: clique em GERAR DIFERENÇA";
  }
}

// ── conexão / coleta ──────────────────────────────────────────────────────────
let manualMode = false;

/**
 * Dica acionável para erros conhecidos de conexão WebUSB.
 * O caso mais comum: outro processo (adb server, Android Studio, scrcpy, outra
 * aba) já segurou o dispositivo, e o WebUSB precisa dele com exclusividade.
 */
function connectionHint(err: Error): string | null {
  const msg = (err.message || "").toLowerCase();
  if (/already in use|in use by another|access denied|unable to claim|claiminterface/.test(msg)) {
    return [
      "Dica: o dispositivo já está sendo usado por outro programa.",
      "  1. Feche Android Studio / scrcpy / app desktop antigo e outras abas deste site.",
      "  2. No terminal, rode:  adb kill-server",
      "  3. Clique em \"Conectar dispositivo\" de novo e autorize a depuração USB no aparelho.",
    ].join("\n");
  }
  return null;
}

async function onConnect() {
  try {
    log("Abrindo seletor de dispositivos USB...");
    const adb = await connect();
    if (!adb) {
      log("Seleção cancelada.", "warn");
      return;
    }
    state.adb = adb;
    setConnected(adb.serial);
    log(`Dispositivo conectado (serial ${adb.serial}).`, "ok");
    refreshButtons();
  } catch (e) {
    const err = e as Error;
    log(`Falha ao conectar: ${err.message}`, "err");
    const hint = connectionHint(err);
    if (hint) log(hint, "warn");
  }
}

async function doCollect(which: "A" | "B") {
  if (!state.adb) {
    log("Nenhum dispositivo conectado.", "err");
    return;
  }
  const btn = which === "A" ? els.btnCollectA : els.btnCollectB;
  btn.disabled = true;
  log(`Coletando Build ${which}...`);
  try {
    const build = await collectBuild(state.adb);

    if (which === "B" && state.buildA && build.serial && build.serial === state.buildA.serial) {
      const ok = confirm(
        "O dispositivo parece ser o MESMO da Build A (mesmo serial).\n" +
          "Isso gera um diff vazio. Continuar mesmo assim?"
      );
      if (!ok) {
        log("Coleta da Build B cancelada (mesmo dispositivo).", "warn");
        refreshButtons();
        return;
      }
    }

    if (which === "A") state.buildA = build;
    else state.buildB = build;

    log(`Build ${which} coletada: ${build.build_id}`, "ok");
    // fecha a conexão para permitir trocar de dispositivo
    await close(state.adb);
    state.adb = null;
    setConnected(null);
  } catch (e) {
    log(`Erro na coleta da Build ${which}: ${(e as Error).message}`, "err");
  } finally {
    refreshButtons();
  }
}

// ── gerar diff ────────────────────────────────────────────────────────────────
async function onGenerate() {
  if (!state.buildA || !state.buildB) return;
  log("Gerando relatório...");
  els.btnGenerate.disabled = true;
  try {
    const res = await fetch("/api/diff", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ build_a: state.buildA, build_b: state.buildB, format: "html" }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const html = await res.text();
    state.lastReportHtml = html;
    els.report.srcdoc = html;
    els.report.classList.remove("hidden");
    log("Relatório gerado.", "ok");
  } catch (e) {
    log(`Erro ao gerar relatório: ${(e as Error).message}`, "err");
  } finally {
    refreshButtons();
  }
}

function onDownload() {
  if (!state.lastReportHtml) return;
  const blob = new Blob([state.lastReportHtml], { type: "text/html" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  const name = `${state.buildA?.build_id ?? "A"}_vs_${state.buildB?.build_id ?? "B"}.html`;
  a.href = url;
  a.download = name.replace(/[^\w.-]/g, "_");
  a.click();
  URL.revokeObjectURL(url);
}

function onReset() {
  state.buildA = null;
  state.buildB = null;
  state.lastReportHtml = null;
  els.btnCollectA.textContent = "COLETAR BUILD A";
  els.btnCollectB.textContent = "COLETAR BUILD B";
  els.report.classList.add("hidden");
  els.report.removeAttribute("srcdoc");
  log("Estado resetado.", "warn");
  refreshButtons();
}

// ── presets ─────────────────────────────────────────────────────────────────
async function openPresets(target: "A" | "B") {
  state.presetTarget = target;
  els.presetTitle.textContent = `Presets — aplicar à Build ${target}`;
  await renderPresetList();
  els.presetDialog.showModal();
}

async function renderPresetList() {
  els.presetList.innerHTML = "Carregando...";
  try {
    const res = await fetch("/api/presets");
    if (res.status === 503) {
      els.presetList.innerHTML = "<i>Banco de presets não configurado (DATABASE_URL).</i>";
      return;
    }
    const presets: any[] = await res.json();
    if (!presets.length) {
      els.presetList.innerHTML = "<i>Nenhum preset salvo.</i>";
      return;
    }
    els.presetList.innerHTML = "";
    for (const p of presets) {
      const item = document.createElement("div");
      item.className = "item";
      const load = document.createElement("button");
      load.className = "btn small";
      load.textContent = `${p.nome} — ${p.build_id}`;
      load.onclick = () => applyPreset(p);
      const del = document.createElement("button");
      del.className = "btn small ghost";
      del.textContent = "🗑";
      del.onclick = () => deletePreset(p.id);
      item.append(load, del);
      els.presetList.appendChild(item);
    }
  } catch (e) {
    els.presetList.innerHTML = `<i>Erro: ${(e as Error).message}</i>`;
  }
}

function applyPreset(p: any) {
  // presets guardam props como dict; o backend aceita string OU dict via apk_info,
  // mas /api/diff espera strings de props. Reconvertendo dict -> texto getprop.
  const propsText = Object.entries(p.props || {})
    .map(([k, v]) => `[${k}]: [${v}]`)
    .join("\n");
  const build: CollectedBuild = {
    build_id: p.build_id,
    serial: "",
    props: propsText,
    packages: p.packages || "",
    features: p.features || "",
  };
  if (state.presetTarget === "A") state.buildA = build;
  else state.buildB = build;
  log(`Preset "${p.nome}" aplicado à Build ${state.presetTarget}.`, "ok");
  els.presetDialog.close();
  refreshButtons();
}

async function deletePreset(id: string) {
  if (!confirm("Excluir este preset?")) return;
  await fetch(`/api/presets/${id}`, { method: "DELETE" });
  await renderPresetList();
}

async function savePreset() {
  const nome = els.presetName.value.trim();
  if (!nome) {
    alert("Informe um nome para o preset.");
    return;
  }
  const build = state.presetTarget === "A" ? state.buildA : state.buildB;
  if (!build) {
    alert(`Colete a Build ${state.presetTarget} antes de salvar.`);
    return;
  }
  // converte props (texto getprop) -> dict para armazenar
  const props: Record<string, string> = {};
  for (const line of build.props.split("\n")) {
    const m = line.trim().match(/^\[(.+?)\]: \[(.*)?\]$/);
    if (m) props[m[1]] = m[2] ?? "";
  }
  const res = await fetch("/api/presets", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      nome,
      build_id: build.build_id,
      props,
      packages: build.packages,
      features: build.features,
    }),
  });
  if (res.status === 409) {
    alert("Já existe um preset com esse nome.");
    return;
  }
  if (res.status === 503) {
    alert("Banco de presets não configurado.");
    return;
  }
  els.presetName.value = "";
  await renderPresetList();
  log(`Preset "${nome}" salvo.`, "ok");
}

// ── modo manual (dev) ─────────────────────────────────────────────────────────
function applyManual() {
  const target = ($("manualTarget") as HTMLSelectElement).value as "A" | "B";
  const build: CollectedBuild = {
    build_id: ($("manualBuildId") as HTMLInputElement).value || `MANUAL_${target}`,
    serial: "",
    props: ($("manualProps") as HTMLTextAreaElement).value,
    packages: ($("manualPkgs") as HTMLTextAreaElement).value,
    features: ($("manualFeats") as HTMLTextAreaElement).value,
  };
  if (target === "A") state.buildA = build;
  else state.buildB = build;
  log(`Build ${target} preenchida manualmente (${build.build_id}).`, "ok");
  refreshButtons();
}

// ── init ──────────────────────────────────────────────────────────────────────
function init() {
  if (!isSupported()) {
    els.unsupported.classList.remove("hidden");
    log("WebUSB indisponível — use Chrome/Edge. Modo manual ainda funciona.", "warn");
  }

  els.btnConnect.onclick = onConnect;
  els.btnCollectA.onclick = () => doCollect("A");
  els.btnCollectB.onclick = () => doCollect("B");
  els.btnPresetA.onclick = () => openPresets("A");
  els.btnPresetB.onclick = () => openPresets("B");
  els.btnGenerate.onclick = onGenerate;
  els.btnDownload.onclick = onDownload;
  els.btnReset.onclick = onReset;
  els.btnPresetSave.onclick = savePreset;
  $("btnManualApply").onclick = applyManual;

  els.btnManual.onclick = () => {
    manualMode = !manualMode;
    els.manualPanel.classList.toggle("hidden", !manualMode);
    els.manualPanel.open = manualMode;
    refreshButtons();
  };

  refreshButtons();
  log("Pronto. Conecte um dispositivo (Chrome/Edge) ou use o modo manual.");
}

init();
