# AI Candidate Ranking System

An MVP that ranks job candidates by **understanding resume meaning**, not just keyword matching. It combines **SentenceTransformers + FAISS** for semantic similarity with **Groq AI (Llama 3.3 70B)** for recruiter-style evaluation.

## Features

- Upload job description (text or PDF)
- Upload multiple resume PDFs
- Parse resumes into structured fields (name, skills, experience, education, projects, certifications)
- Generate embeddings with `all-MiniLM-L6-v2` and store in FAISS
- Semantic similarity ranking between job description and resumes
- Groq AI evaluation for each candidate (match score, strengths, gaps, recommendation)
- Final score: **70% semantic similarity + 30% Groq match score**
- Results table with CSV export

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python, FastAPI |
| AI / LLM | Groq API (Llama 3.3 70B) |
| Embeddings | SentenceTransformers (`all-MiniLM-L6-v2`) |
| Vector Search | FAISS |
| Frontend | HTML, CSS, JavaScript |

## Project Structure

```text
CandidateRankingAI/
├── backend/
│   ├── app.py
│   ├── parser.py
│   ├── embeddings.py
│   ├── ranking.py
│   ├── groq_client.py
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── script.js
├── uploads/
├── output/
└── README.md
```

## Prerequisites

- Python 3.10+
- [Groq API key](https://console.groq.com/)

## Setup

1. **Clone the repository**

```bash
git clone <your-repo-url>
cd "AI Ranking System"
```

2. **Create a virtual environment**

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

3. **Install dependencies**

```bash
cd backend
pip install -r requirements.txt
```

4. **Configure environment variables**

Create a `.env` file in the `backend/` directory:

```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```

5. **Run the server**

```bash
cd backend
uvicorn app:app --reload
```

6. **Open the app**

Visit [http://127.0.0.1:8000](http://127.0.0.1:8000)

## Deploy on Vercel

This repository includes a Vercel entrypoint at `api/index.py`, a root `requirements.txt`, and `vercel.json` routing.

1. Push the project to GitHub.
2. Import the repository in Vercel.
3. Add these Environment Variables in Vercel Project Settings:

```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```

4. Deploy with the default Vercel settings.

You can also deploy with the CLI:

```bash
npm i -g vercel
vercel
vercel env add GROQ_API_KEY
vercel env add GROQ_MODEL
vercel --prod
```

Note: Vercel serverless storage is temporary, so uploaded PDFs and CSV output are stored in `/tmp` during a function instance. For permanent storage, connect a database or object storage provider.

## Usage

1. Paste or upload a **Job Description** (text or PDF).
2. Upload one or more **Resume PDFs**.
3. Click **Rank Candidates**.
4. Review ranked results in the table.
5. Click **Download CSV** to export results.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/upload-job` | Upload job description (text and/or PDF) |
| `POST` | `/upload-resumes` | Upload multiple resume PDFs |
| `POST` | `/rank` | Run semantic + Groq ranking |
| `GET` | `/results` | Get latest ranking results |
| `GET` | `/download-csv` | Download ranked candidates CSV |
| `GET` | `/health` | Health check |

### Example: Upload Job Description

```bash
curl -X POST "http://127.0.0.1:8000/upload-job" \
  -F "job_text=We are hiring a Python developer with FastAPI experience."
```

### Example: Upload Resumes

```bash
curl -X POST "http://127.0.0.1:8000/upload-resumes" \
  -F "resume_files=@resume1.pdf" \
  -F "resume_files=@resume2.pdf"
```

### Example: Rank Candidates

```bash
curl -X POST "http://127.0.0.1:8000/rank"
```

## Scoring Formula

```
Final Score = (Semantic Similarity × 0.70) + (Groq Match Score × 0.30)
```

- **Semantic Similarity**: Cosine similarity from FAISS (0–100%)
- **Groq Match Score**: AI recruiter evaluation (0–100)

## Notes

- No login, database, or authentication — all state is in-memory for the session.
- Uploaded files are saved to `uploads/`; CSV output goes to `output/`.
- First run downloads the SentenceTransformer model (~90 MB).

## License

MIT
