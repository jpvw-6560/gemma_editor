import numpy as np
import wave

def create_beep(filename, freq=440, duration_ms=200, volume=0.5, sample_rate=44100):
    t = np.linspace(0, duration_ms / 1000, int(sample_rate * duration_ms / 1000), False)
    # Onde sinus
    tone = np.sin(freq * 2 * np.pi * t)
    # Ajuste le volume
    tone = (tone * volume * 32767).astype(np.int16)
    # Écriture fichier .wav
    with wave.open(filename, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(tone.tobytes())

# Génération des fichiers
create_beep("info.wav", freq=600, duration_ms=150, volume=0.3)
create_beep("success.wav", freq=800, duration_ms=150, volume=0.5)
create_beep("warning.wav", freq=1000, duration_ms=200, volume=0.7)
create_beep("error.wav", freq=400, duration_ms=300, volume=1.0)

print("Fichiers .wav générés : info.wav, success.wav, warning.wav, error.wav")