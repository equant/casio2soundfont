import os
import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write
import time
import yaml

# Load configuration
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)
synth_name = config['synth_name']
presets = config['presets']

print(sd.query_devices())

#DEVICE_NUMBER     = 4
SAMPLE_RATE        = 44100
SILENCE_DURATION   = 2.0
MAX_RECORD_SECONDS = 10
START_THRESHOLD    = 0.01
STOP_THRESHOLD     = 0.005
WAIT_TIMEOUT       = 20

def record_silence(duration=5, fs=SAMPLE_RATE):
    with sd.InputStream(channels=1, samplerate=fs) as stream:
        print("Recording silence for calibration...")
        buffer = []
        for _ in range(int(duration * fs / 1024)):
            data, _ = stream.read(1024)
            buffer.extend(data[:, 0])
    return np.array(buffer)

print("Finding noise floor...")
silence_data = record_silence(SILENCE_DURATION, SAMPLE_RATE)
max_val = np.max(np.abs(silence_data))
min_val = np.min(np.abs(silence_data))
mean_val = np.mean(np.abs(silence_data))
print(f"Silence Test Results: Min: {min_val}, Max: {max_val}, Mean: {mean_val}")
mean_val = np.mean(silence_data)
std_dev = np.std(silence_data)
sigma_3 = mean_val + 3 * std_dev
print(f"Mean Value: {mean_val}")
print(f"3 Sigma: {sigma_3}")

# Prompt user to choose the threshold
print(f"Current START_THRESHOLD: {START_THRESHOLD}")
use_max_val = input(f"Do you want to use twice the Max value from silence test ({2*max_val}) as the new START_THRESHOLD? (yes/no): ").strip().lower()
if use_max_val == 'yes':
    START_THRESHOLD = max_val * 10
    STOP_THRESHOLD  = START_THRESHOLD/2


def record_note(fs=SAMPLE_RATE,
                max_record_seconds=MAX_RECORD_SECONDS,
                start_threshold=START_THRESHOLD,
                stop_threshold=STOP_THRESHOLD,
                silence_duration=SILENCE_DURATION,
                wait_timeout=WAIT_TIMEOUT):

    def is_silent(data, threshold):
        return np.max(np.abs(data)) < threshold

    with sd.Stream(channels=1, samplerate=fs) as stream:
        print("Recording... play the note.")
        buffer = []
        started = False
        silent_for = 0
        start_time = time.time()

        while True:
            data, overflowed = stream.read(int(fs * 0.5))  # Read in chunks
            if overflowed:
                print("Overflow! Recording may not be clean.")
                return None

            if not started and (time.time() - start_time) > wait_timeout:
                print("No note detected within the timeout period.")
                return None

            if not started and np.max(np.abs(data)) > start_threshold:
                started = True
                note_start_time = time.time()

            if started:
                buffer.extend(data[:, 0])
                if is_silent(data, stop_threshold):
                    silent_for += 1
                    if silent_for >= int(silence_duration / 0.5):
                        break
                else:
                    silent_for = 0

                if (time.time() - note_start_time) > max_record_seconds:
                    break

    return np.array(buffer)


for preset_name, settings in presets.items():
    # Create directory for the preset
    print()
    print(f"{synth_name}")
    print(f"{preset_name}")
    preset_dir = f"{synth_name}_{preset_name}"
    os.makedirs(preset_dir, exist_ok=True)
    
    for note_name, midi_code in settings['notes'].items():
        # Prompt user to play the note
        #input(f"Prepare to play the note {note_name}. Press Enter to start listening.")
        print(f"Recording the note {note_name}...")

        # Record the audio
        #audio = record_note(MAX_RECORD_SECONDS, FS, THRESHOLD, SILENCE_DURATION)
        audio = record_note()

        if audio is not None:
            # Save the files
            note_file = f"{preset_dir}/{note_name}.wav"
            midi_file = f"{preset_dir}/{midi_code}.wav"
            #write("recorded_note.wav", SAMPLE_RATE, audio)
            write(note_file, SAMPLE_RATE, audio)
            write(midi_file, SAMPLE_RATE, audio)
            print(f"Saved {note_name} as {note_file} and MIDI {midi_code} as {midi_file}")
        else:
            print("Gave up waiting.")



print("All notes recorded.")

