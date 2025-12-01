import asyncio
import sounddevice as sd
import soundfile as sf
import numpy as np
import os

try:
    import resampy
except ImportError:
    resampy = None

try:
    from pydub import AudioSegment
except Exception:
    AudioSegment = None

DEFAULT_DEVICES = [16, 17]

def _ensure_2d(data):
    if data.ndim == 1:
        return data[:, None]
    return data

def _apply_volume_and_clip(data, factor):
    out = data * float(factor)
    np.clip(out, -1.0, 1.0, out=out)
    return out

def load_audio_as_float32(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".mp3" or (ext not in [".wav", ".flac", ".ogg", ".aiff"] and AudioSegment is not None):
        if AudioSegment is None:
            raise RuntimeError("pydub vereist voor mp3")
        seg = AudioSegment.from_file(path)
        sr = seg.frame_rate
        samples = np.array(seg.get_array_of_samples(), dtype=np.float32)
        if seg.channels > 1:
            samples = samples.reshape((-1, seg.channels))
        else:
            samples = samples.reshape((-1, 1))
        samples /= float(2 ** (8 * seg.sample_width - 1))
        return samples, sr
    else:
        data, sr = sf.read(path, dtype="float32", always_2d=True)
        return data, int(sr)

async def _play_on_device(arr, sr, device_index):
    info = sd.query_devices(device_index)
    dev_sr = int(info['default_samplerate'])
    dev_channels = info['max_output_channels']

    # channel handling
    out = arr
    if dev_channels < arr.shape[1]:
        if dev_channels == 1:
            out = np.mean(arr, axis=1)[:, None]
        else:
            out = arr[:, :dev_channels]
    else:
        if arr.shape[1] == 1 and dev_channels > 1:
            out = np.repeat(arr, dev_channels, axis=1)

    if sr != dev_sr:
        if resampy is None:
            raise RuntimeError("resampy vereist voor resampling")
        out = resampy.resample(out.T, sr, dev_sr).T.astype('float32')

    def blocking():
        with sd.OutputStream(samplerate=dev_sr, device=device_index,
                             channels=out.shape[1], dtype='float32') as stream:
            stream.write(out)

    await asyncio.to_thread(blocking)

async def play_array(arr, sr, devices=None):
    if devices is None:
        devices = DEFAULT_DEVICES
    await asyncio.gather(*[_play_on_device(arr, sr, d) for d in devices])

def play_sync(path, devices=None, volume=1.0):
    # sync wrapper: decode from file
    asyncio.run(play(path, devices, volume))

def play_array_sync(arr, sr, devices=None):
    asyncio.run(play_array(arr, sr, devices))
