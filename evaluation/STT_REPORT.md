# STT Accuracy Report

Accuracy is measured only for languages with human-recorded reference clips.
No fabricated audio or invented WER percentages.

## Status

No reference clips found under `evaluation/stt_reference/<lang>/`.
All languages: **not measured**.

To measure: add `clip.webm` + `clip.txt` per language, set `OPENAI_API_KEY`, then run:

```
python -m evaluation.stt_wer
```
