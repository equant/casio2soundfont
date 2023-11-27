import librosa
import numpy as np
import tqdm

def find_seamless_loop(audio, sr, min_loop_duration=1.0):
    # Function to calculate the similarity between two waveforms
    def waveform_similarity(wave1, wave2):
        return np.mean(np.abs(wave1 - wave2))

    # Minimum loop length in samples
    min_loop_length = int(min_loop_duration * sr)
    half_sample = len(audio) // 2
    best_score = float('inf')
    best_loop_start = 0
    best_loop_end = half_sample

    # Search for loop points
    tqdmloop = tqdm.tqdm(range(0, half_sample - min_loop_length))
    for loop_start in tqdmloop:
        for loop_end in range(loop_start + min_loop_length, half_sample):
            loop1 = audio[loop_start:loop_end]
            loop2 = audio[loop_end:loop_end + (loop_end - loop_start)]
            
            # Calculate similarity
            score = waveform_similarity(loop1, loop2)
            if score < best_score:
                best_score = score
                best_loop_start, best_loop_end = loop_start, loop_end

    return best_loop_start, best_loop_end

audio, sr = librosa.load("recordings/Casio Casiotone MT-70/pipe organ/pipe organ-E3.wav", sr=None)

# Find the best loop points
loop_start, loop_end = find_seamless_loop(audio, sr)

print(f"Best loop from {loop_start} to {loop_end}")

