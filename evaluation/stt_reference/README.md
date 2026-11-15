# STT reference clips

Place **human-recorded** audio here. Do not commit fabricated synthetic speech.

```
evaluation/stt_reference/
  en/
    sample1.webm
    sample1.txt          # exact expected transcript
  am/
    sample1.wav
    sample1.txt
```

Supported languages: `en`, `am`, `ti`, `om`, `so`, `ar`.

Then run:

```
python -m evaluation.stt_wer
python -m evaluation.voice_latency --base http://127.0.0.1:8000
```
