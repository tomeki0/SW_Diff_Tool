// Coleta de dados do dispositivo Android via WebADB (WebUSB).
// API verificada contra @yume-chan/adb 2.6.0.
import { Adb, AdbDaemonTransport } from "@yume-chan/adb";
import { AdbDaemonWebUsbDeviceManager } from "@yume-chan/adb-daemon-webusb";
import AdbWebCredentialStore from "@yume-chan/adb-credential-web";

export interface CollectedBuild {
  build_id: string;
  serial: string;
  props: string;
  packages: string;
  features: string;
}

const CREDENTIAL_APP_NAME = "SW Diff Tool";

/** WebUSB só existe em navegadores Chromium (Chrome/Edge/Opera/Brave). */
export function isSupported(): boolean {
  return (
    typeof navigator !== "undefined" &&
    "usb" in navigator &&
    AdbDaemonWebUsbDeviceManager.BROWSER !== undefined
  );
}

/**
 * Abre o seletor de dispositivos USB do navegador, autentica e devolve um Adb.
 * Retorna null se o usuário cancelar a seleção.
 */
export async function connect(): Promise<Adb | null> {
  const manager = AdbDaemonWebUsbDeviceManager.BROWSER;
  if (!manager) {
    throw new Error("WebUSB não disponível neste navegador.");
  }

  const device = await manager.requestDevice();
  if (!device) {
    return null; // usuário cancelou o chooser
  }

  const connection = await device.connect();
  const credentialStore = new AdbWebCredentialStore(CREDENTIAL_APP_NAME);

  const transport = await AdbDaemonTransport.authenticate({
    serial: device.serial,
    connection,
    credentialStore,
  });

  return new Adb(transport);
}

/** Roda um comando one-shot e devolve todo o stdout como string. */
async function shellCollect(adb: Adb, command: string): Promise<string> {
  return adb.subprocess.noneProtocol.spawnWaitText(command);
}

/**
 * Coleta as 3 saídas brutas + display id de uma build.
 * Sequencial de propósito (mais robusto que streams concorrentes no daemon).
 */
export async function collectBuild(adb: Adb): Promise<CollectedBuild> {
  const props = await shellCollect(adb, "getprop");
  const packages = await shellCollect(adb, "pm list packages -f");
  const features = await shellCollect(adb, "pm list features");
  const displayId = await shellCollect(adb, "getprop ro.build.display.id");

  return {
    props,
    packages,
    features,
    build_id: displayId.trim(),
    serial: adb.serial ?? "",
  };
}

export async function close(adb: Adb): Promise<void> {
  try {
    await adb.close();
  } catch {
    // ignora erros ao fechar (device já desconectado etc.)
  }
}
