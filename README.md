# RepoRepair

A Flask web app that finds and repairs errors in a GitHub repository using Retrieval-Augmented Generation (RAG) and an LLM agent.

## How it works

1. Enter a GitHub repository URL.
2. The app clones the repo and runs static analysis and automated tests to find errors, with file and line numbers.
3. Source code is split into chunks, embedded, and stored in a local ChromaDB vector database.
4. An LLM agent uses RAG retrieval to get the relevant code context and proposes fixes.
5. Each fix is validated by rerunning the tests.
6. The app shows the results and lets you download a Markdown report.

## Tech stack

Python, Flask, Google Gemini API, ChromaDB, embeddings, static code analysis, automated testing.

## Setup

1. Clone the repository and go into the project folder:
   ```bash
   git clone https://github.com/Ananyapulluri/RepoRepair.git
   cd RepoRepair/majorr
   ```
2. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set your Gemini API key as an environment variable. Don't hardcode it in the code.
   ```bash
   # Windows PowerShell
   $env:GEMINI_API_KEY="your_key_here"
   ```
4. Run the app:
   ```bash
   python app.py
   ```
5. Open http://localhost:5002 and enter a GitHub repository URL.

## Notes

- The app stores only one report in memory, so it's meant for local use. Multi-user deployment would need per-session storage.
- Keep your API key out of version control. The `.gitignore` excludes `.env` and the local `chroma_db/` folder.
