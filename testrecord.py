import sounddevice as sd
import numpy as np
import time

def record_audio(fs, duration):
    print("Recording...")
    recording = sd.rec(int(duration * fs), samplerate=fs, channels=1)
    sd.wait()  # Wait for the recording to finish
    return recording

fs = 44100  # Sample rate
duration = 5  # Duration in seconds

# Record and save the audio
audio = record_audio(fs, duration)
audio = audio.flatten()  # Ensuring it's a 1D array

# Saving the recorded audio
from scipy.io.wavfile import write
write("test_recording.wav", fs, audio)

