import os
import player
import threading

hotkeyMap = {}  # key -> (filename, volume_factor)
soundCache = {}  # key -> (numpy_array, samplerate, volume)
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
    token = token.strip()
    if token == "":
        return DEFAULT_VOLUME
    if token.lower().endswith("db"):
        try:
            db = float(token[:-2])
            factor = 10 ** (db / 20.0)
            return factor
        except Exception:
            return DEFAULT_VOLUME
    try:
        return float(token)
    except Exception:
        return DEFAULT_VOLUME

def initialize():
    global hotkeyMap, soundCache
    hotkeyMap = {}
    soundCache = {}

    if not os.path.exists("keymap.txt"):
        print("keymap.txt niet gevonden — maak er één met regels als: Key.space=ding.mp3,0.5")
        return

    for raw in open("keymap.txt", "r", encoding="utf-8").read().splitlines():
        line = raw.strip()
        if line == "" or line.startswith("#"):
            continue
        if "=" not in line:
            print("Ignoring malformed line:", line)
            continue
        left, right = line.split("=", 1)
        key = left.strip().strip("'").strip('"')
        parts = [p.strip().strip("'").strip('"') for p in right.split(",", 1)]
        filename = parts[0]
        vol = DEFAULT_VOLUME
        if len(parts) > 1:
            vol = _parse_volume_token(parts[1])
        hotkeyMap[key] = (filename, vol)

    # preload all sounds into numpy cache
    for key, (filename, vol) in hotkeyMap.items():
        fullPath = os.path.join(soundFolder, filename)
        if not os.path.exists(fullPath):
            print(f"File not found during preload: {fullPath}")
            continue
        try:
            arr, sr = player.load_audio_as_float32(fullPath)
            arr = player._apply_volume_and_clip(arr, vol)  # volume applied at preload
            soundCache[key] = (arr, sr)
        except Exception as e:
            print(f"Error preloading {filename} for key {key}: {e}")

    print("Loaded keymap:", hotkeyMap)
    print("Cached keys:", list(soundCache.keys()))

def play(key):
    keystr = keyToStr(key)
    try:
        if keystr not in hotkeyMap:
            print(f"hotkey not found: {keystr} in dictionary")
            return
        if keystr not in soundCache:
            print(f"Sound not cached for key: {keystr}, falling back to disk")
            filename, vol = hotkeyMap[keystr]
            fullPath = os.path.join(soundFolder, filename)
            threading.Thread(target=player.play_sync, args=(fullPath, [16,17], vol), daemon=True).start()
            return
        arr, sr = soundCache[keystr]
        # spawn a thread to play cached array on devices
        threading.Thread(target=player.play_array_sync, args=(arr, sr, [16,17]), daemon=True).start()
    except Exception as e:
        print("Error while trying to play:", e)
