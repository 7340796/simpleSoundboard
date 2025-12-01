from pynput import keyboard
import soundboard

pressedKeys = set({}) # stores all held down keys, for implementing key click, not key hold stuff

def on_press(key, injected):
    if key in pressedKeys:  # key is already being pressed 
        return
    pressedKeys.add(key)    # add key to the pressed keys if its not already in it
    
    # stop when delete is pressed
    if key == keyboard.Key.delete:  
        print("Quitting SoundBoard...")
        return False
    
    # trigger sound
    soundboard.play(key)


def on_release(key, injected):
    pressedKeys.discard(key)

# Collect events until released
with keyboard.Listener(
        on_press=on_press,
        on_release=on_release) as listener:
    soundboard.initialize()
    listener.join()
