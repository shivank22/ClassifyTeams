# ClassifyTeams

Two small utilities to process Microsoft Teams channel exports:

1) `anonymize_messages.py`  
   Reads a Teams `messages.json`, groups by `conversationIdentity.conversationId`, and writes a clean JSON with
   `thread_id` and `messages` (`user.displayName` is fixed to `XXXX`).

2) `classify_threads.py`  
   Calls the OpenAI Chat Completions API for each thread and writes classifications
   (`Incident Number`, `Root Cause`, `Type`, `Severity`) to an output JSON.

## Requirements

- Python 3.8+
- An OpenAI API key for classification

## Usage

### 1) Anonymize and group threads

```bash
python3 anonymize_messages.py \
  --input /path/to/messages.json \
  --output /path/to/anonymized_threads.json
```

### 2) Classify threads

```bash
OPENAI_API_KEY=... python3 classify_threads.py \
  --input /path/to/anonymized_threads.json \
  --output /path/to/thread_classifications.json
```

## Notes

- `classify_threads.py` uses the default OpenAI base URL and `gpt-4.1-mini` model.
- Add `--keep-html` to `anonymize_messages.py` if you want raw message HTML.
