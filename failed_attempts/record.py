import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
import yaml
import os
import time

# Load configuration
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)
synth_name = config['synth_name']
presets = config['presets']

print(sd.query_devices())

DEVICE_NUMBER = 4
FS = 44100  # Sample rate
THRESHOLD = 0.001  # Audio threshold to start recording, adjust as needed
SILENCE_DURATION = 2.0  # Duration of silence in seconds to stop recording
MAX_RECORD_SECONDS = 10  # Max record time

def record_note(duration, fs, threshold, silence_duration):
    def callback(indata, frames, time, status):
        if status:
            print("Status:", status)
        max_val = np.max(indata[:, 0])
        print("Max indata:", max_val)
        if max_val > threshold:
            print("Threshold exceeded:", max_val)
            nonlocal note_detected
            note_detected = True

    # Buffer to store audio chunks and flag for note detection
    buffer = []
    note_detected = False

    # Set up a stream to listen for the note
    with sd.InputStream(callback=callback, channels=1, samplerate=fs):
        print("Listening for note...")
        while not note_detected:
            sd.sleep(100)

    if note_detected:
        print("Note detected, starting recording...")
        start_time = time.time()
        with sd.InputStream(channels=1, samplerate=fs) as stream:
            while True:
                data, overflowed = stream.read(int(fs * 0.5))
                if overflowed:
                    print("Overflow! Recording may not be clean.")
                buffer.append(data)
                current_time = time.time()
                if (current_time - start_time > duration) or (np.max(data) < threshold and current_time - start_time > silence_duration):
                    print("Stopping recording.")
                    break

    return np.concatenate(buffer, axis=0) if buffer else None

for preset_name, settings in presets.items():
    # Create directory for the preset
    preset_dir = f"{synth_name}_{preset_name}"
    os.makedirs(preset_dir, exist_ok=True)
    
    for note_name, midi_code in settings['notes'].items():
        # Prompt user to play the note
        input(f"Prepare to play the note {note_name}. Press Enter to start listening.")

        # Record the audio
        audio = record_note(MAX_RECORD_SECONDS, FS, THRESHOLD, SILENCE_DURATION)

        # Trim silence from the beginning
        audio_trimmed = audio[np.abs(audio) > THRESHOLD]

        # Save the files
        note_file = f"{preset_dir}/{note_name}.wav"
        midi_file = f"{preset_dir}/{midi_code}.wav"

        write(note_file, FS, audio_trimmed)
        write(midi_file, FS, audio_trimmed)
        print(f"Saved {note_name} as {note_file} and MIDI {midi_code} as {midi_file}")

print("All notes recorded.")

