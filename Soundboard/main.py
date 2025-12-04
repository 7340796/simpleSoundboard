from pynput import keyboard
import os
import soundfile as sf
import sounddevice as sd
import numpy as np

d = ["CABLE Input (VB-Audio Virtual Cable)", "Luidsprekers (Realtek(R) Audio)", ]
pressedKeys = set({}) # stores all held down keys, for implementing key click, not key hold stuff
def play():
    # create numpy array with audio data
    device = "Luidsprekers (Realtek (R) Audio) WASAPI"
    path = os.path.join(os.getcwd(), "sounds", "toink.wav")
    data, samplerate = sf.read(path)
    device_info = sd.query_devices(device)
    device_samplerate = device_info['default_samplerate']
    sd.play(data, device_samplerate, device = device)

def on_press(key, injected):
    if key in pressedKeys:  # key is already being pressed 
        return
    pressedKeys.add(key)    # add key to the pressed keys if its not already in it
    
    # stop when delete is pressed
    if key == keyboard.Key.delete:  
        print("Quitting SoundBoard...")
        return False
    
    # trigger sound
    if key == keyboard.Key.space:
        play()

def on_release(key, injected):
    pressedKeys.discard(key)

# Collect events until released
with keyboard.Listener(
        on_press=on_press,
        on_release=on_release) as listener:
    listener.join()
