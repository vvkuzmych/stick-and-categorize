"""Spike B: transcribe a short clip with faster-whisper and print model, time and text.

Throwaway. Run: python spikes/transcribe_spike.py CLIP.wav [model]   (default model: small)
"""
import sys
import time

from faster_whisper import WhisperModel


def main() -> None:
    clip = sys.argv[1]
    size = sys.argv[2] if len(sys.argv) > 2 else "small"

    t0 = time.perf_counter()
    model = WhisperModel(size, device="cpu", compute_type="int8")
    load_s = time.perf_counter() - t0

    t0 = time.perf_counter()
    segments, info = model.transcribe(clip)
    text = " ".join(s.text.strip() for s in segments)
    run_s = time.perf_counter() - t0

    print(f"model={size} load={load_s:.1f}s transcribe={run_s:.1f}s "
          f"audio={info.duration:.1f}s speed={info.duration / run_s:.1f}x realtime "
          f"lang={info.language}")
    print(text)


if __name__ == "__main__":
    main()
