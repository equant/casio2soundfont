import os
import numpy as np
import sounddevice as sd
import yaml
import time
from scipy.io.wavfile import write

# Load configuration
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)
synth_name = config['synth_name']
presets = config['presets']

print(sd.query_devices())

#DEVICE_NUMBER = 4
FS = 44100  # Sample rate
THRESHOLD = 0.001  # Audio threshold to start recording, adjust as needed
SILENCE_DURATION = 2.0  # Duration of silence in seconds to stop recording
MAX_RECORD_SECONDS = 5  # Max record time

def record_note(duration, fs, threshold, pre_recording_buffer_duration=0.5):
    def callback(indata, frames, time, status):
        nonlocal note_detected, pre_recording_buffer
        if status:
            print("Status:", status)

        # Extend the pre-recording buffer
        pre_recording_buffer.extend(indata[:, 0])

        # Detect threshold
        if np.max(indata[:, 0]) > threshold and not note_detected:
            print("Threshold exceeded")
            note_detected = True

    # Initialize variables
    note_detected = False
    pre_recording_buffer = []

    # Listening loop
    with sd.InputStream(callback=callback, channels=1, samplerate=fs):
        print("Listening for note...")
        while not note_detected:
            sd.sleep(100)

    # Keep only the relevant part of the pre_recording buffer
    buffer_length = int(fs * pre_recording_buffer_duration)
    buffer = pre_recording_buffer[-buffer_length:]

    # Recording loop
    print("Note detected, starting recording...")
    with sd.InputStream(channels=1, samplerate=fs) as stream:
        start_time = time.time()
        while time.time() - start_time < duration:
            data, overflowed = stream.read(int(fs * 0.5))
            if overflowed:
                print("Overflow! Recording may not be clean.")
            buffer.extend(data[:, 0])

    return np.array(buffer)

# Record a note
#audio = record_note(duration, fs, threshold)
#write("recorded_note.wav", fs, audio)

for preset_name, settings in presets.items():
    # Create directory for the preset
    preset_dir = f"{synth_name}_{preset_name}"
    os.makedirs(preset_dir, exist_ok=True)
    
    for note_name, midi_code in settings['notes'].items():
        # Prompt user to play the note
        input(f"Prepare to play the note {note_name}. Press Enter to start listening.")

        # Record the audio
        #audio = record_note(MAX_RECORD_SECONDS, FS, THRESHOLD, SILENCE_DURATION)
        audio = record_note(MAX_RECORD_SECONDS, FS, THRESHOLD)

        # Trim silence from the beginning
        #audio_trimmed = audio[np.abs(audio) > THRESHOLD]
        audio_trimmed = audio

        # Save the files
        note_file = f"{preset_dir}/{note_name}.wav"
        midi_file = f"{preset_dir}/{midi_code}.wav"

        write(note_file, FS, audio_trimmed)
        write(midi_file, FS, audio_trimmed)
        print(f"Saved {note_name} as {note_file} and MIDI {midi_code} as {midi_file}")

print("All notes recorded.")

