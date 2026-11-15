"""Unit tests for WER/CER helpers (no API, no audio)."""

from evaluation.stt_wer import cer, levenshtein, normalize_text, wer


def test_levenshtein_and_wer_basic():
    assert levenshtein(["a", "b"], ["a", "b"]) == 0
    assert levenshtein(["a", "b"], ["a", "c"]) == 1
    assert wer("hello world", "hello world", "en") == 0.0
    assert wer("hello world", "hello there", "en") == 0.5
    assert cer("ab", "ab") == 0.0
    assert cer("ab", "ac") == 0.5


def test_normalize_keeps_ethiopic_tokens():
    tokens = normalize_text("ሰላም ዓለም!", "am")
    assert "ሰላም" in tokens
    assert "ዓለም" in tokens
