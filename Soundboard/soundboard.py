import os
import player
import threading

hotkeyMap = {}  # key -> (filename, volume_factor)
soundFolder = os.path.join(os.getcwd(), "sounds")
DEFAULT_VOLUME = 1.0

def keyToStr(key):
    try:
        if hasattr(key, "char") and key.char is not None:
            return key.char
        else:
            return str(key)
    except Exception:
        return str(key)

def _parse_volume_token(token):
    """
    Parse a volume token which can be:
      - a float factor e.g. 0.5
      - a dB string e.g. +3dB or -6dB
    Returns float factor.
    """
    token = token.strip()
    if token == "":
        return DEFAULT_VOLUME
    # dB notation
    if token.lower().endswith("db"):
        try:
            db = float(token[:-2])
            factor = 10 ** (db / 20.0)
            return factor
        except Exception:
            return DEFAULT_VOLUME
    # numeric factor
    try:
        return float(token)
    except Exception:
        return DEFAULT_VOLUME

def initialize():
    global hotkeyMap
    hotkeyMap = {}
    if not os.path.exists("keymap.txt"):
        print("keymap.txt niet gevonden — maak er één met regels als: Key.space=ding.mp3,0.5")
        return

    with open("keymap.txt", "r", encoding="utf-8") as f:
        for raw in f.read().splitlines():
            line = raw.strip()
            if line == "" or line.startswith("#"):
                continue
            if "=" not in line:
                print("Ignoring malformed line:", line)
                continue
            left, right = line.split("=", 1)
            key = left.strip().strip("'").strip('"')
            # right can be "file" or "file,volume"
            parts = [p.strip().strip("'").strip('"') for p in right.split(",", 1)]
            filename = parts[0]
            vol = DEFAULT_VOLUME
            if len(parts) > 1:
                vol = _parse_volume_token(parts[1])
            hotkeyMap[key] = (filename, vol)
    print("Loaded keymap:", hotkeyMap)

def play(key):
    keystr = keyToStr(key)
    try:
        filename, volume = hotkeyMap[keystr]
        fullPath = os.path.join(soundFolder, filename)
        if not os.path.exists(fullPath):
            print("File not found:", fullPath)
            return
        print(f"Playing: {filename} at volume {volume}")
        # start playback in background so the listener keeps running
        threading.Thread(target=player.play_sync, args=(fullPath, [16,17], volume), daemon=True).start()
    except KeyError:
        print(f"hotkey not found: {keystr} in dictionary: {hotkeyMap}")
    except Exception as e:
        print("Error while trying to play:", e)
