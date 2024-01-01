import glob
import random
import librosa
import numpy as np
import sounddevice as sd
import matplotlib.pyplot as plt

def in_seconds(n_samples, sr):
    return n_samples / sr

def find_seamless_loop_new(audio, sr, 
                       search_start_fraction = 0.1,
                       min_loop_length_fraction = 0.1,
                       window_size_fraction = 0.75):
    """
    search_start_fraction       how far into the audio to look for the start of the loop
    min_loop_length_fraction    the minimum size loop we want (as fraction of audio sample).
                                This is used to set the point at which we stop looking for an end point.
    window_size_fraction        We only want to find a good match for the beginning of the loop, we don't
                                have to match the whole loop.
    """

    # Define the minimum length of the loop
    min_loop_length = int(len(audio) * min_loop_length_fraction)

    # Find a suitable starting point for the loop
    search_start_point = int(len(audio) * search_start_fraction)
    loop_start_point = find_zero_crossing(audio, search_start_point)

    # Define the point to stop searching for a loop end
    start_searching_point = loop_start_point + min_loop_length

    # Calculate the size of the window used for matching the end of the loop
    window_size = int(len(audio) * min_loop_length_fraction * window_size_fraction)

    # The initial window of audio for comparison
    start_window = audio[loop_start_point:loop_start_point + window_size]

    # Variables to track the best loop found
    best_match_score = float('inf')
    best_loop_end_point = None

    # Iterate to the end of the audio to find the loop end
    for potential_end_point in range(start_searching_point, len(audio)-window_size):
        current_end_window = audio[potential_end_point:potential_end_point + window_size]

        # Check if the windows are of the same size, skip if not
        if len(current_end_window) != len(start_window):
            continue

        # Calculate similarity score
        current_score = waveform_similarity(start_window, current_end_window)

        # Update best score and loop end point if current is better
        if current_score <= best_match_score:
            best_match_score = current_score
            best_loop_end_point = potential_end_point

    # Return the loop start and end points if a suitable loop is found
    if best_loop_end_point is not None:
        return loop_start_point, best_loop_end_point, best_match_score, start_window
    else:
        return None, None, None  # Indicate that no suitable loop was found


def find_zero_crossing_old(audio, start_index):
    for i in range(start_index, len(audio)):
        if audio[i] * audio[i-1] < 0:
            return i
    return start_index  # Fallback if no zero-crossing is found

def find_zero_crossing(audio, start_index, direction='forward'):
    """
    Find the first zero-crossing point in the audio signal.

    :param audio: The audio data (numpy array).
    :param start_index: Index to start the search from.
    :param direction: 'forward' for forward search, 'reverse' for backward search.
    :return: Index of the zero-crossing point.
    """
    if direction == 'forward':
        for i in range(start_index, len(audio)):
            if audio[i] * audio[i-1] < 0:
                return i
    elif direction == 'reverse':
        for i in range(start_index, 0, -1):
            if audio[i] * audio[i-1] < 0:
                return i
    return start_index  # Fallback if no zero-crossing is found

# Example usage
# forward_search = find_zero_crossing(audio_data, start_index)


def waveform_similarity(wave1, wave2):
    return np.mean(np.abs(wave1 - wave2))


    # Define search start and end points within the audio
    search_start_point = int(len(audio) * 0.30)
    search_end_point = int(len(audio) * 0.60)


def find_seamless_loop_recommented(audio, sr, fraction_for_loop_search, min_loop_length_ratio=0.05):
    # Calculate the size of the loop to be searched based on the given fraction
    search_loop_size = int(len(audio) * fraction_for_loop_search)

    # Define search start and end points within the audio
    search_start_point = int(len(audio) * 0.30)
    search_end_point = int(len(audio) * 0.60)

    # Define the minimum length of the loop
    min_loop_length = int(len(audio) * min_loop_length_ratio)

    # Find a suitable starting point for the loop
    loop_start_point = find_zero_crossing(audio, search_start_point)

    # The initial window of audio for comparison
    comparison_window = audio[loop_start_point:loop_start_point + search_loop_size]

    # Variables to track the best loop found
    best_match_score = float('inf')
    best_loop_end_point = None

    # Iterate over possible end points for the loop
    for potential_end_point in range(search_end_point + search_loop_size, loop_start_point, -1):
        if potential_end_point - search_loop_size < loop_start_point + min_loop_length:
            continue  # Skip if the loop length is less than the minimum required

        # The window of audio to compare against the start window
        current_end_window = audio[potential_end_point - search_loop_size:potential_end_point]

        # Calculate similarity score
        current_score = waveform_similarity(comparison_window, current_end_window)

        # Update best score and loop end point if current is better
        if current_score < best_match_score:
            best_match_score = current_score
            best_loop_end_point = potential_end_point

    # Return the loop start and end points if a suitable loop is found
    if best_loop_end_point is not None:
        return loop_start_point, best_loop_end_point - search_loop_size, best_match_score
    else:
        return None, None, None  # Indicate that no suitable loop was found


def find_seamless_loop_old(audio, sr, fraction_of_expected_loop, min_loop_length_frac=0.05):
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


def play_loop_with_intro(audio, sr, loop_start, loop_end, repeat_times=10):
    intro_audio = audio[:loop_start]
    outro_audio = audio[loop_end:]
    loop_audio = audio[loop_start:loop_end]
    looped_audio = np.tile(loop_audio, repeat_times)
    full_audio = np.concatenate((intro_audio, looped_audio, outro_audio))
    sd.play(full_audio, sr, blocksize=1024*3)
    sd.wait()  # Wait for the playback to finish

find_seamless_loop = find_seamless_loop_old

def plot_waveform(audio, sr, loop_start=None, loop_end=None, title='Audio Waveform'):
    """
    Plot the waveform of an audio signal.

    :param audio: The audio data (numpy array) or a list of audio data arrays.
    :param sr: Sample rate of the audio data.
    :param loop_start: Sample index where the loop starts (optional).
    :param loop_end: Sample index where the loop ends (optional).
    :param title: Title of the plot (optional).
    """
    if not isinstance(audio, list):
        audio = [audio]

    # Create subplots for each audio array in the list
    fig, axs = plt.subplots(len(audio), 1, figsize=(10, 4 * len(audio)))
    if len(audio) == 1:
        axs = [axs]  # Make sure axs is always a list
    for i, a in enumerate(audio):
        axs[i].plot(a)
        axs[i].set_title(f'{title} - Track {i+1}')
        axs[i].set_xlabel('Sample Index')
        axs[i].set_ylabel('Amplitude')
        if i == len(a):
            if loop_start is not None:
                axs[i].axvline(loop_start, c="red", label='Loop Start')
            if loop_end is not None:
                axs[i].axvline(loop_end, c="green", label='Loop End')
            axs[i].legend()
    plt.tight_layout()
    plt.show()

def test():
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

        # Example usage
        play_loop_with_intro(audio, sr, loop_start, loop_end, repeat_times=10)
