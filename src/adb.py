import subprocess

ADB = ["adb"]
DEFAULT_TIMEOUT = 12

def rodar_adb(comando):
    try:
        res = subprocess.run(
            ADB + comando,
            capture_output=True,
            text=True,
            timeout=DEFAULT_TIMEOUT
        )

        if res.returncode == 0:
            return res.stdout
        else:
            print(f"[ADB ERROR] {res.stderr.strip()}")
            return None

    except Exception as e:
        print(f"[ADB EXCEPTION] {e}")
        return None


def get_device_id():
    return adb_shell(["getprop", "ro.build.display.id"])


def is_device_connected():
    out = rodar_adb(["get-state"])
    return True if out and "device" in out else False


def get_serial():
    out = rodar_adb(["get-serialno"])
    return out.strip() if out else None


def coletar_dados():
    props = adb_shell(["getprop"])
    pkgs  = adb_shell(["pm", "list", "packages", "-f"])
    feats = adb_shell(["pm", "list", "features"])
    return props, pkgs, feats

def adb_shell(cmd):
    return rodar_adb(["shell"] + cmd)