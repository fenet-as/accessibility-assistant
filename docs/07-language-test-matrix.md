# Language test matrix (Milestone 2)

Honest status: **verified** languages have passed the automated matrix below.
**experimental** languages are exposed in the UI and Telegram picker but are not claimed as production-ready.

| Code | Name | Status | Detection | Override | Greeting | Refusal | Notes |
|------|------|--------|-----------|----------|----------|---------|-------|
| en | English | verified | pass | pass | pass | pass | Default Latin |
| am | Amharic | verified | pass | pass | pass | pass | Ethiopic; preferred on Ge'ez ties |
| ti | Tigrinya | experimental | pass | pass | pass | pass | Needs more content translations |
| om | Afaan Oromo | experimental | pass | pass | pass | pass | Latin markers |
| so | Somali | experimental | pass | pass | pass | pass | Latin markers |
| ar | Arabic | experimental | pass | pass | pass | pass | RTL UI |

Run: `pytest tests/test_languages.py tests/test_language_matrix.py -q`

Telegram: `/start` or `/lang` shows all six languages; experimental ones are marked with `*`. Preference is stored in SQLite `channel_prefs`.
