# Podcast Search with Gemini File Search API
This project is a simple command-line tool that demonstrates how to build a searchable podcast knowledge base using the [Gemini File Search API](https://ai.google.dev/gemini-api/docs/file-search).

It consists of two main scripts:
*   `ingest.py`: Ingests a podcast RSS feed, downloads audio, transcribes episodes using the fast Gemini 2.5 Flash-Lite model, and uploads them to a File Search Store.
*   `query.py`: Allows you to ask natural language questions about the ingested podcast content and receive grounded answers with citations.

## Prerequisites
*   Python 3.10+
*   A Gemini API key (get one from [Google AI Studio](https://aistudio.google.com/app/apikey)).

## Setup
1.  Create and activate a virtual environment:
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```
    On Windows:
    ```bash
    python -m venv .venv
    .venv\Scripts\activate
    ```

2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

3.  Create a `.env` file and add your API key:
    
    **Important:** The `.env` file must be saved in UTF-8 encoding to avoid errors.
    
    **On macOS/Linux:**
    ```bash
    echo "GOOGLE_API_KEY=your_api_key_here" > .env
    ```
    
    **On Windows (PowerShell):**
    ```powershell
    Set-Content -Path .env -Value "GOOGLE_API_KEY=your_api_key_here" -Encoding UTF8
    ```
    
    **Manual Creation (All Platforms):**
    
    Create a new file named `.env` in the project root and add:
    ```
    GOOGLE_API_KEY=your_actual_api_key_here
    ```
    **Save as UTF-8 encoding** (not UTF-16 or with BOM):
    - In VS Code: File → Save with Encoding → UTF-8
    - In Notepad: Save As → Encoding → UTF-8
    - In Notepad++: Encoding → UTF-8

## Usage
### 1. Ingest a Podcast
Run `ingest.py` with the RSS feed URL of the podcast you want to index. You can use the `--limit` flag to restrict the number of episodes processed.

**Important:** Use a real podcast RSS feed URL, not example.com.

**Example with Lex Fridman Podcast (recommended):**
```bash
python ingest.py "https://feeds.simplecast.com/tOjNXec5" --limit 3
```

**Other Popular Podcasts:**
```bash
# The Joe Rogan Experience
python ingest.py "https://joeroganexp.libsyn.com/rss" --limit 3

# Huberman Lab
python ingest.py "https://hubermanlab.libsyn.com/rss" --limit 3

# All-In Podcast
python ingest.py "https://feeds.megaphone.fm/all-in" --limit 3
```

This will:
*   Create a new File Search Store named "Podcasts" (if it doesn't exist).
*   Download the specified number of recent episodes.
*   Transcribe them using Gemini 2.5 Flash-Lite.
*   Upload the transcripts, with metadata, to the store.

Optionally pass `--store "My Store Name"` to specify a custom File Store name:
```bash
python ingest.py "https://feeds.simplecast.com/tOjNXec5" --limit 3 --store "Lex Fridman Archive"
```

### 2. Ask a Question
Once ingestion is complete, use `query.py` to ask questions:
```bash
python query.py "What was the main topic discussed in the latest episode?"
```

**More example queries:**
```bash
python query.py "Who were the guests in the episodes about AI?"
python query.py "What did they say about consciousness?"
python query.py "Summarize the discussion about quantum computing"
```

Gemini will search the indexed transcripts and provide an answer based on the actual content, complete with citations.

## Troubleshooting

**UnicodeDecodeError when loading .env file:**
```
UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff in position 0
```
Your `.env` file is saved in the wrong encoding (likely UTF-16). Delete the file and recreate it using one of the methods in the Setup section above, ensuring it's saved as UTF-8.

**"No such file or directory: .env":**

Make sure you've created the `.env` file in the project root directory (same location as `ingest.py` and `query.py`).

**API Key Issues:**

If you get authentication errors:
1. Verify your API key is correct at [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Ensure there are no extra spaces or quotes in your `.env` file
3. The line should look exactly like: `GOOGLE_API_KEY=AIzaSy...`

**RSS Feed Not Working:**

Make sure you're using a valid podcast RSS feed URL. If a feed doesn't work, try:
1. Opening the URL in a browser to verify it returns XML
2. Using one of the example feeds listed above
3. Finding the RSS feed URL from the podcast's official website

## Notes
*   The first ingestion may take some time depending on the number and length of episodes.
*   Transcription uses the fast Gemini 2.5 Flash-Lite model for cost and speed efficiency.
*   Transcripts are stored with metadata (title, description, publish date) for better search results.