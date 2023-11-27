import glob
import random
import librosa
import numpy as np
import tqdm
import sounddevice as sd


def find_zero_crossing(audio, start_index):
    for i in range(start_index, len(audio)):
        if audio[i] * audio[i-1] < 0:
            return i
    return start_index  # Fallback if no zero-crossing is found

def waveform_similarity(wave1, wave2):
    return np.mean(np.abs(wave1 - wave2))

def find_seamless_loop(audio, sr, fraction_of_expected_loop, min_loop_length_frac=0.05):
    expected_loop_size = int(len(audio) * fraction_of_expected_loop)
    start_search_point = int(len(audio) * 0.30)
    end_search_point = int(len(audio) * 0.60)
    min_loop_length = int(len(audio) * min_loop_length_frac)  # Convert min loop length to samples

    loop_start = find_zero_crossing(audio, start_search_point)
    window_size = expected_loop_size
    start_window = audio[loop_start:loop_start + window_size]
    best_match_score = float('inf')
    best_loop_end = None

    for loop_end in range(end_search_point + window_size, loop_start, -1):
        if loop_end - window_size < loop_start + min_loop_length:
            continue  # Ensure minimum loop length

        end_window = audio[loop_end - window_size:loop_end]

        score = waveform_similarity(start_window, end_window)
        if score < best_match_score:
            best_match_score = score
            best_loop_end = loop_end

    if best_loop_end is not None:
        return loop_start, best_loop_end - window_size, best_match_score
    else:
        return None, None, None  # No suitable loop found

def find_seamless_loop_old(audio, sr):
    start_search_point = int(len(audio) * 0.3)
    end_search_point = int(len(audio) * 0.60)

    loop_start = find_zero_crossing(audio, start_search_point)
    best_match_score = float('inf')
    best_loop_end = end_search_point

    print(f"Length: {len(audio)}")
    print(f"Start point moved: {start_search_point} -> {loop_start}")
    print(f"End search point:  {end_search_point}")

    tqdmloop = tqdm.tqdm(range(end_search_point, loop_start, -1))
    for loop_end in range(end_search_point, loop_start, -1):  # Slide window backwards
        window_size = loop_end - loop_start
        if loop_start - window_size < 0:
            print(f"window size: {window_size}")
            print("loop_start - window_size < 0")
            break

        start_window = audio[loop_start - window_size:loop_start]
        end_window = audio[loop_end - window_size:loop_end]
        
        score = waveform_similarity(start_window, end_window)
        if score < best_match_score:
            best_match_score = score
            best_loop_end = loop_end

    return loop_start, best_loop_end, best_match_score


wave_files = glob.glob("recordings/Casio Casiotone MT-11/*/*.wav")
random.shuffle(wave_files)

for w in wave_files:
    print(w)
    audio, sr = librosa.load(w, sr=None)

    # Find the best loop points

    fraction_of_expected_loop = 0.2
    loop_start, loop_end, score = find_seamless_loop(audio, sr, fraction_of_expected_loop)
    if loop_start is not None and loop_end is not None:
        print(f"Best loop from {loop_start} to {loop_end}. Score: {score}")
    else:
        print("No suitable loop found.")

    def play_loop_with_intro(audio, sr, loop_start, loop_end, repeat_times=10):
        intro_audio = audio[:loop_start]
        outro_audio = audio[loop_end:]
        loop_audio = audio[loop_start:loop_end]
        looped_audio = np.tile(loop_audio, repeat_times)
        full_audio = np.concatenate((intro_audio, looped_audio, outro_audio))
        sd.play(full_audio, sr)
        sd.wait()  # Wait for the playback to finish

    # Example usage
    play_loop_with_intro(audio, sr, loop_start, loop_end, repeat_times=10)
