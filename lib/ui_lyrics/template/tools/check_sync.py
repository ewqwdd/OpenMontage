"""Check that the audio inside a rendered MP4 is sample-aligned with the source excerpt."""
import subprocess, sys, tempfile, os
import numpy as np, soundfile as sf
mp4, wav = sys.argv[1], sys.argv[2]
tmp = os.path.join(tempfile.mkdtemp(), "a.wav")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", mp4, "-ac", "1", "-ar", "44100", tmp], check=True)
a, sr = sf.read(tmp); b, sr2 = sf.read(wav)
if b.ndim > 1: b = b.mean(1)
n = min(len(a), len(b), sr * 10); a, b = a[:n], b[:n]
lag = np.arange(-4000, 4001)
best = max(lag, key=lambda L: float(np.dot(a[max(0, L):n + min(0, L)], b[max(0, -L):n - max(0, L)])))
print(f"audio offset in mp4 vs source: {best} samples = {best / sr * 1000:.1f} ms; mp4 audio {len(a) / sr:.3f}s")
