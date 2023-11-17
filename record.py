import os
import itertools
import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write
import time
import yaml


print(sd.query_devices())

#DEVICE_NUMBER     = 4
SAMPLE_RATE        = 44100
SILENCE_DURATION   = 2.0
MAX_RECORD_SECONDS = 10
START_THRESHOLD    = 0.01
STOP_THRESHOLD     = 0.005
WAIT_TIMEOUT       = 20

def get_white_keys(start, end):
    all_notes = ['C', 'D', 'E', 'F', 'G', 'A', 'B']
    start_octave = int(start[1])
    end_octave = int(end[1])
    notes = []

    for octave in range(start_octave, end_octave + 1):
        for note in all_notes:
            note_name = f"{note}{octave}"
            if note_name == start:
                notes.append(note_name)
            elif note_name == end:
                notes.append(note_name)
                return notes
            elif notes:
                notes.append(note_name)

    return notes

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
        #print("Recording... play the note.")
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


# Load configuration
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)
synth_name = config['synth_name']
presets = config['presets']
notes_range = config['notes']
settings = config['settings']

setting_combinations = list(itertools.product(['on', 'off'], repeat=len(settings)))
setting_dicts = []
for combination in setting_combinations:
    setting_dict = {settings[i]: combination[i] for i in range(len(settings))}
    setting_dicts.append(setting_dict)

if len(notes_range) == 2:
    # We grab white key notes between first and last
    notes = get_white_keys(notes_range[0], notes_range[1])
else:
    notes = notes_range


#        audio = record_note()
#
#        if audio is not None:
#            # Save the files
#            note_file = f"{preset_dir}/{note_name}.wav"
#            midi_file = f"{preset_dir}/{midi_code}.wav"
#            #write("recorded_note.wav", SAMPLE_RATE, audio)
#            write(note_file, SAMPLE_RATE, audio)
#            write(midi_file, SAMPLE_RATE, audio)
#            print(f"Saved {note_name} as {note_file} and MIDI {midi_code} as {midi_file}")
#        else:
#            print("Gave up waiting.")

print(f"Synth: {synth_name}")
print()
for preset in presets:
    print(f"  {preset}")
    for setting_dict in setting_dicts:
        print(f"  {preset}")
        print(f"  {setting_dict}")
        input("Hit enter when you have the settings ready.")
        good_recording = False
        while not good_recording:
            for note in notes:
                print(f"    {note}")
                # Create directories
                dir_name = f"{synth_name}/{preset}"
                os.makedirs(dir_name, exist_ok=True)

                # Set up file name
                filename_part = "-".join([f"{key}_{value}" for key, value in setting_dict.items()])
                file_name = f"{preset}-{filename_part}-V127-{note}.wav"
                file_path = os.path.join(dir_name, file_name)

                # Record the audio
                print(f"    Recording {file_name}...")
                audio_data = record_note()

                if audio_data is not None:
                    # Save the recording
                    write(file_path, SAMPLE_RATE, audio_data)
                    print(f"    ...Saved {file_path}")
                else:
                    print("Gave up waiting.")
            answer = input("Good?  Should we move on? (y/n)").strip().lower()
            if answer == "y":
                good_recording = True


