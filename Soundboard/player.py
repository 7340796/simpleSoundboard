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

# Default device indices (pas aan naar jouw indices indien nodig)
DEFAULT_DEVICES = [16, 17]

def _ensure_2d(data):
    if data.ndim == 1:
        return data[:, None]
    return data

def _apply_volume_and_clip(data, factor):
    """
    data: numpy array float32 in [-1,1], shape (N,channels)
    factor: linear multiplier
    returns clipped float32 array
    """
    out = data * float(factor)
    # prevent clipping artifacts by hard clipping to [-1,1]
    np.clip(out, -1.0, 1.0, out=out)
    return out

def load_audio_as_float32(path):
    """
    Load audio file and return (data, samplerate) where data is float32 numpy array
    shape (frames, channels) and values in [-1.0, 1.0].
    Supports: wav/ogg/flac/aiff via soundfile, mp3 via pydub (ffmpeg).
    """
    ext = os.path.splitext(path)[1].lower()
    if ext == ".mp3" or (ext not in [".wav", ".flac", ".ogg", ".aiff"] and AudioSegment is not None):
        if AudioSegment is None:
            raise RuntimeError("pydub niet beschikbaar — mp3 support vereist pydub + ffmpeg.")
        seg = AudioSegment.from_file(path)
        sr = seg.frame_rate
        samples = seg.get_array_of_samples()
        arr = np.asarray(samples)
        channels = seg.channels
        sample_width = seg.sample_width
        dtype_max = float(2 ** (8 * sample_width - 1))
        if channels > 1:
            arr = arr.reshape((-1, channels))
        else:
            arr = arr.reshape((-1,))
        arr = arr.astype("float32") / dtype_max
        arr = _ensure_2d(arr)
        return arr, sr
    else:
        data, sr = sf.read(path, dtype="float32", always_2d=True)
        return data, int(sr)

async def play(path, devices=None, volume=1.0):
    """
    Async play path on list of device indices. Resamples per-device if needed.
    volume: linear multiplier (1.0 default). Per-key volume is applied BEFORE resampling.
    """
    if devices is None:
        devices = DEFAULT_DEVICES

    if not os.path.exists(path):
        raise FileNotFoundError(path)

    data, sr = load_audio_as_float32(path)   # data shape (N, channels)
    data = _ensure_2d(data)

    # apply volume now (before resample)
    data = _apply_volume_and_clip(data, volume)

    async def _play_on_device(device_index):
        info = sd.query_devices(device_index)
        dev_sr = int(info['default_samplerate'])
        dev_channels = info['max_output_channels']

        # Channel handling: if device supports fewer channels, mix down
        if dev_channels < data.shape[1]:
            if dev_channels == 1:
                out = np.mean(data, axis=1)[:, None]
            else:
                out = data[:, :dev_channels]
        else:
            if data.shape[1] == 1 and dev_channels > 1:
                out = np.repeat(data, dev_channels, axis=1)
            else:
                out = data

        # Resample if needed
        if sr != dev_sr:
            if resampy is None:
                raise RuntimeError("Resampling nodig maar 'resampy' is niet geïnstalleerd. Run: pip install resampy")
            out = resampy.resample(out.T, sr, dev_sr).T.astype('float32')

        # blocking OutputStream write inside thread so event loop stays responsive
        def blocking_play():
            with sd.OutputStream(samplerate=dev_sr,
                                 device=device_index,
                                 channels=out.shape[1],
                                 dtype='float32') as stream:
                stream.write(out)

        await asyncio.to_thread(blocking_play)

    # Run all device plays in parallel and wait for them to finish
    await asyncio.gather(*[_play_on_device(d) for d in devices])

def play_sync(path, devices=None, volume=1.0):
    """Convenience sync wrapper to call from non-async code."""
    asyncio.run(play(path, devices, volume))
