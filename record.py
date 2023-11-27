import os, glob, random
import itertools
import numpy as np
import sounddevice as sd
import librosa
import scipy.io.wavfile
import wave
import time
import yaml
import casioloopdetect

print(sd.query_devices())

config_file = "casio_MT-70.yaml"

#DEVICE_NUMBER     = 4
TESTING            = True
SAMPLE_RATE        = 44100
SILENCE_DURATION   = 2.0
MAX_RECORD_SECONDS = 10
START_THRESHOLD    = 0.01
STOP_THRESHOLD     = 0.005
WAIT_TIMEOUT       = 20
TARGET_PEAK_DB     = -1 # dB
TARGET_PEAK        = 10 ** (TARGET_PEAK_DB / 20)
PLAY_LOOPS         = True # If you trust the loop detection, make this False and it'll be much faster.

def get_white_keys(start, end):
    white_keys = ['C', 'D', 'E', 'F', 'G', 'A', 'B']
    start_octave = int(start[1])
    end_octave = int(end[1])
    notes = []

    for octave in range(start_octave, end_octave + 1):
        for note in white_keys:
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


def trim_silence(audio_data, threshold):
    # Find the first index where audio exceeds the threshold
    start_index = next((i for i, sample in enumerate(audio_data) if abs(sample) > threshold*0.9), None)

    # Find the last index where audio exceeds the threshold
    end_index = next((i for i, sample in enumerate(reversed(audio_data)) if abs(sample) > threshold*0.333), None)

    if start_index is not None and end_index is not None:
        trimmed_audio = audio_data[start_index:-end_index]
    else:
        trimmed_audio = audio_data

    return trimmed_audio


def record_note(fs=SAMPLE_RATE,
                max_record_seconds=MAX_RECORD_SECONDS,
                start_threshold=START_THRESHOLD,
                stop_threshold=STOP_THRESHOLD,
                silence_duration=SILENCE_DURATION,
                wait_timeout=WAIT_TIMEOUT):

    def is_silent(data, threshold):
        return np.max(np.abs(data)) < threshold

    with sd.Stream(channels=1, samplerate=fs) as stream:
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

def amplitude_to_db(amplitude):
    return 20 * np.log10(abs(amplitude))

def normalize_audio(audio_data, target_peak, current_peak):
    return audio_data * (target_peak / current_peak)

##################################################
#         Calculate Noise and Thresholds         #
##################################################

print("Finding noise floor...")
silence_data = record_silence(SILENCE_DURATION, SAMPLE_RATE)
max_noise_val = np.max(np.abs(silence_data))
min_noise_val = np.min(np.abs(silence_data))
mean_noise_val = np.mean(np.abs(silence_data))
print(f"Silence Test Results: Min: {min_noise_val}, Max: {max_noise_val}, Mean: {mean_noise_val}")
mean_noise_val = np.mean(silence_data)
std_dev = np.std(silence_data)
sigma_3 = mean_noise_val + 3 * std_dev
print(f"Mean Value: {mean_noise_val}")
print(f"3 Sigma: {sigma_3}")

# START and STOP thresholds are used for detecting audio.  I.e., when to start and stop recording.
# The STOP_THRESHOLD is used to calculated the TRIM_THRESHOLD, which is used to trim the audio
# after the recording has been completed.

# Prompt user to choose the threshold
print(f"Current START_THRESHOLD: {START_THRESHOLD}")
suggested_start_threshold = max_noise_val * 10
use_max_val = input(f"Do you want to use 10 times the Max value from silence test ({suggested_start_threshold}) as the new START_THRESHOLD? (yes/no): ").strip().lower()
if use_max_val == 'yes':
    START_THRESHOLD = suggested_start_threshold
    STOP_THRESHOLD  = START_THRESHOLD/2

TRIM_THRESHOLD = STOP_THRESHOLD + max_noise_val


##################################################
#                 Configuration                  #
##################################################

with open(config_file, 'r') as f:
    synth_config = yaml.safe_load(f)
synth_name = synth_config['synth_name']
presets = synth_config['presets']
notes_range = synth_config['notes']

if len(notes_range) == 2:
    # We grab white key notes between first and last
    notes = get_white_keys(notes_range[0], notes_range[1])
else:
    notes = notes_range

if TESTING:
    #notes = notes[::4]
    notes = notes[::8]

##################################################
#                      Main                      #
##################################################


print(f"Synth: {synth_name}")
print()
for preset in presets:
    peak_amplitudes = {}
    print(f"  {preset}")
    preset_name = preset['name']
    do_loop = preset['loop']
    input("Hit enter when you have the settings ready.")
    good_recording = False
    while not good_recording:
        for note in notes:
            print(f"    {note}")
            dir_name = f"recordings/{synth_name}/{preset_name}"
            os.makedirs(dir_name, exist_ok=True)

            file_name = f"{preset_name}-{note}.wav"
            file_path = os.path.join(dir_name, file_name)

            print(f"    Recording {file_name}...")
            audio_data = record_note()

            if audio_data is not None:
                peak_amplitude = np.max(np.abs(audio_data))
                peak_db = amplitude_to_db(peak_amplitude)
                peak_amplitudes[file_path] = peak_amplitude
                print(f"Peak Volume Level: {peak_db} dB")
                trimmed_audio = trim_silence(audio_data, TRIM_THRESHOLD)  # Or use another threshold based on your noise floor analysis
                scipy.io.wavfile.write(file_path, SAMPLE_RATE, trimmed_audio)
                print(f"    ...Saved {file_path}")
            else:
                print("Gave up waiting.")
        answer = input("Good?  Should we normalize and move on? (y/n)").strip().lower()
        if answer == "y":
            good_recording = True

    overall_peak = max(peak_amplitudes.values())

    print("Normalizing and loop detection...")
    for file_path, peak_amplitude in peak_amplitudes.items():
        print(f"Normalizing {file_path}")
        fs, audio_data = scipy.io.wavfile.read(file_path)
        normalized_audio = normalize_audio(audio_data, TARGET_PEAK, overall_peak)
        # Overwrite the file with normalized audio
        scipy.io.wavfile.write(file_path, fs, normalized_audio)

        if not do_loop:
            print("Preset doesn't require loop finding.  Skipping loop finding.")
            continue

        audio, sr = librosa.load(file_path, sr=None)
        fraction_of_expected_loop = 0.2
        loop_start, loop_end, score = casioloopdetect.find_seamless_loop(audio, sr, fraction_of_expected_loop)

        if PLAY_LOOPS:
            ANSWER = False
            while(ANSWER == False):
                print(f"Playing detected loop for {file_path}")
                casioloopdetect.play_loop_with_intro(audio, sr, loop_start, loop_end, repeat_times=7)
                yes_no = input("Use loop? (y/n)")
                if yes_no == "n":
                    with open(os.path.join(dir_name, "bad_loops.txt"), "a") as badloopf:
                        badloopf.write(f"{file_path},{loop_start},{loop_end},{score}\n")
                    ANSWER = True
                    continue
                if yes_no == "y":
                    ANSWER = True

        if loop_start is not None and loop_end is not None:
            print(f"Best loop from {loop_start} to {loop_end}. Score: {score}")
            with open(os.path.join(dir_name, "selected_loops.txt"), "a") as goodloopf:
                goodloopf.write(f"{file_path},{loop_start},{loop_end},{score}\n")
        else:
            print("No suitable loop found.")
            with open(os.path.join(dir_name, "bad_loops.txt"), "a") as badloopf:
                badloopf.write(f"{file_path}\n")

    print("...done.")
