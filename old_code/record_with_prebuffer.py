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

def record_note(duration, fs, threshold, silence_duration, pre_recording_buffer_duration=0.5):
    def callback(indata, frames, time, status):
        nonlocal note_detected
        if note_detected:
            # Return early if note is already detected
            return

        if status:
            print("Status:", status)

        max_val = np.max(indata[:, 0])
        print("Max indata:", max_val)
        if max_val > threshold:
            print("Threshold exceeded:", max_val)
            note_detected = True

        # Flatten the indata and extend the pre_recording buffer
        pre_recording_buffer.extend(indata[:, 0])

    buffer = []
    note_detected = False
    pre_recording_buffer = []

    with sd.InputStream(callback=callback, channels=1, samplerate=fs):
        print("Listening for note...")
        while not note_detected:
            sd.sleep(100)

    # Calculate the number of frames to keep in the pre-recording buffer
    buffer_length = int(fs * pre_recording_buffer_duration)

    if note_detected:
        print("Note detected, starting recording...")
        start_time = time.time()
        # Append only the relevant part of the pre_recording buffer
        buffer.extend(pre_recording_buffer[-buffer_length:])
        with sd.InputStream(channels=1, samplerate=fs) as stream:
            while True:
                data, overflowed = stream.read(int(fs * 0.5))
                if overflowed:
                    print("Overflow! Recording may not be clean.")
                buffer.extend(data[:, 0])  # Flatten and extend the buffer
                current_time = time.time()
                if (current_time - start_time > duration) or (np.max(data) < threshold and current_time - start_time > silence_duration):
                    print("Stopping recording.")
                    break

    # Concatenate the buffer into a single array
    return np.array(buffer) if buffer else None


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
        #audio_trimmed = audio[np.abs(audio) > THRESHOLD]
        audio_trimmed = audio

        # Save the files
        note_file = f"{preset_dir}/{note_name}.wav"
        midi_file = f"{preset_dir}/{midi_code}.wav"

        write(note_file, FS, audio_trimmed)
        write(midi_file, FS, audio_trimmed)
        print(f"Saved {note_name} as {note_file} and MIDI {midi_code} as {midi_file}")

print("All notes recorded.")

