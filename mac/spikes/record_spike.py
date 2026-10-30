"""Spike A: record the microphone with AVAudioEngine to a WAV file and ask for permission.

Throwaway. Run: python record_spike.py [seconds] [out.wav]   (default 5, clip.wav)
"""
import sys
import time

import AVFoundation as AV
from Foundation import NSURL, NSDate, NSRunLoop


def request_permission() -> bool:
    status = AV.AVCaptureDevice.authorizationStatusForMediaType_(AV.AVMediaTypeAudio)
    print("mic authorization status (0=ask,1=restricted,2=denied,3=ok):", status, flush=True)
    if status == 3:
        return True
    if status != 0:
        return False
    result = {}
    AV.AVCaptureDevice.requestAccessForMediaType_completionHandler_(
        AV.AVMediaTypeAudio, lambda granted: result.setdefault("granted", granted))
    while "granted" not in result:
        NSRunLoop.currentRunLoop().runUntilDate_(NSDate.dateWithTimeIntervalSinceNow_(0.1))
    return bool(result["granted"])


def main() -> None:
    seconds = float(sys.argv[1]) if len(sys.argv) > 1 else 5.0
    out = sys.argv[2] if len(sys.argv) > 2 else "clip.wav"
    if not request_permission():
        sys.exit("Microphone permission denied. Enable it in System Settings > Privacy > Microphone.")

    engine = AV.AVAudioEngine.alloc().init()
    node = engine.inputNode()
    fmt = node.outputFormatForBus_(0)
    audio_file, err = AV.AVAudioFile.alloc().initForWriting_settings_error_(
        NSURL.fileURLWithPath_(out), fmt.settings(), None)
    if audio_file is None:
        sys.exit(f"cannot open {out}: {err}")

    def tap(buffer, _when) -> None:
        audio_file.writeFromBuffer_error_(buffer, None)

    node.installTapOnBus_bufferSize_format_block_(0, 4096, fmt, tap)
    ok, err = engine.startAndReturnError_(None)
    if not ok:
        sys.exit(f"engine failed: {err}")
    print(f"recording {seconds}s ... speak now", flush=True)
    end = time.time() + seconds
    while time.time() < end:
        NSRunLoop.currentRunLoop().runUntilDate_(NSDate.dateWithTimeIntervalSinceNow_(0.1))
    node.removeTapOnBus_(0)
    engine.stop()
    print("saved", out, flush=True)


if __name__ == "__main__":
    main()
