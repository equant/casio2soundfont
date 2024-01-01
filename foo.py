import casioloopdetect
import librosa

# recordings/Casio Casiotone MT-70/wood wind/wood wind-B3.wav,44114,80130,0.036664582788944244,good

import matplotlib.pyplot as plt

# Example usage:
# plot_waveform(your_audio_data, your_sample_rate)


fraction_of_expected_loop = 0.2

#for fraction_of_expected_loop in [0.05, 0.1, 0.2, 0.4, 0.6]:
for fraction_of_expected_loop in [0.2]:

    print(f"fraction_of_expected_loop: {fraction_of_expected_loop}")
    file_path='recordings/Casio Casiotone MT-70/pipe organ/pipe organ-C1.wav'
    file_path='recordings/Casio Casiotone MT-70/pipe organ/pipe organ-D4.wav'
    file_path='recordings/Casio Casiotone MT-70/flute/flute-C1.wav'
    audio, sr = librosa.load(file_path, sr=None)
    loop_start, loop_end, score = casioloopdetect.find_seamless_loop(audio, sr, fraction_of_expected_loop=0.2)

    plot_waveform(audio, sr, loop_start=loop_start, loop_end=loop_end, title=file_path)

    loop_frames = loop_end - loop_start
    duration_seconds = loop_frames / sr
    print(f"Score:  {score}")
    print(f"Length: {duration_seconds:0.4f} seconds")

    print(f"Playing detected loop for {file_path}")
    loop_audio, looped_audio = casioloopdetect.play_loop_with_intro(audio, sr, loop_start, loop_end, repeat_times=5)
    print()
