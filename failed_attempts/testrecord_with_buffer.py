import numpy as np
import sounddevice as sd
import time

def record_note(duration, fs, threshold, pre_recording_buffer_duration=0.5):
    def callback(indata, frames, time, status):
        nonlocal note_detected, pre_recording_buffer
        if status:
            print("Status:", status)

        # Extend the pre-recording buffer
        pre_recording_buffer.extend(indata[:, 0])
        max_value = np.max(indata[:, 0])
        min_value = np.min(indata[:, 0])
        print(f"Range: {min_value} -> {max_value}")

        # Detect threshold
        if np.max(indata[:, 0]) > threshold and not note_detected:
            print("Threshold exceeded")
            note_detected = True

    # Initialize variables
    note_detected = False
    pre_recording_buffer = []
    buffer = []  # Main recording buffer

    # Listening loop
    with sd.InputStream(callback=callback, channels=1, samplerate=fs):
        print("Listening for note...")
        while not note_detected:
            sd.sleep(100)

    # Keep only the relevant part of the pre_recording buffer
    buffer_length = int(fs * pre_recording_buffer_duration)
    pre_buffer = pre_recording_buffer[-buffer_length:]

    # Recording loop
    print("Note detected, starting recording...")
    with sd.InputStream(channels=1, samplerate=fs) as stream:
        start_time = time.time()
        while time.time() - start_time < duration:
            data, overflowed = stream.read(int(fs * 0.5))
            if overflowed:
                print("Overflow! Recording may not be clean.")
            buffer.extend(data[:, 0])

    # Merge pre_buffer and buffer with a crossfade if both are present
    if pre_buffer and buffer:
        fade_length = min(len(pre_buffer), len(buffer), int(fs * 0.01))  # 10ms fade
        for i in range(fade_length):
            crossfade_ratio = i / fade_length
            buffer[i] = pre_buffer[-fade_length + i] * (1 - crossfade_ratio) + buffer[i] * crossfade_ratio
        merged_buffer = pre_buffer[:-fade_length] + buffer
    else:
        merged_buffer = pre_buffer + buffer

    return np.array(merged_buffer)

# Record a note
fs = 44100  # Sample rate
duration = 5  # Duration to record after note detection in seconds
#threshold = 0.025  # Adjust as needed
threshold = 0.001  # Adjust as needed

audio = record_note(duration, fs, threshold)
from scipy.io.wavfile import write
audio_int16 = np.int16(audio / np.max(np.abs(audio)) * 32767)
write("recorded_note.wav", fs, audio)
