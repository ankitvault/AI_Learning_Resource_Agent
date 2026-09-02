# AI Study Resource Agent

A complete full-stack AI Study Resource Agent web application designed to help school students in India prepare for their exams. Powered by React (Vite), FastAPI, and the Anthropic Claude API (using `claude-sonnet-4-20250514` with the Web Search tool enabled to fetch real, accurate, and up-to-date links).

## Project Structure

```
study-agent/
├── backend/
│   ├── main.py
│   ├── agent.py
│   ├── requirements.txt
│   └── .env
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── App.css
│       └── components/
│           ├── InputForm.jsx
│           ├── StudyPack.jsx
│           ├── SectionCard.jsx
│           └── Loader.jsx
└── README.md
```

## Setup Instructions

### 1. Get an API Key (Groq or Anthropic)
**Option A: Groq API Key (Recommended / Free Tier)**
- Visit the [Groq Cloud Console](https://console.groq.com/keys).
- Create a new API Key and copy it.

**Option B: Anthropic API Key**
- Visit the [Anthropic Console](https://console.anthropic.com/).
- Create a new secret key and copy it.

### 2. Backend Setup
Navigate to the backend directory, install the dependencies, and configure your API key:

```bash
cd backend
```

Open `backend/.env` and paste your copied API key corresponding to your chosen provider:
```env
ANTHROPIC_API_KEY=your_api_key_here
GROQ_API_KEY=your_groq_api_key_here
```

Install Python dependencies:
```bash
pip install -r requirements.txt
```

Run the FastAPI backend server:
```bash
uvicorn main:app --reload
```
The backend server will run on `http://localhost:8000`.

### 3. Frontend Setup
Open a new terminal window/tab, navigate to the frontend directory, install dependencies, and start the development server:

```bash
cd frontend
npm install
npm run dev
```
The Vite development server will start on `http://localhost:5173` and proxy API requests to the backend automatically.

## How to Use the App
1. Open your browser and navigate to `http://localhost:5173`.
2. Select your **Board** (e.g., CBSE, ICSE, Maharashtra Board) and **Class** level.
3. Enter the **Subject** (e.g., Science) and the specific **Topic** you want to study (e.g., Light - Reflection and Refraction).
4. Click **Generate Study Pack →**.
5. Wait while Claude browses the web to curate real study materials, recommended YouTube videos, question papers, marking schemes, and creates a concise topic summary.
6. Explore the generated study pack cards and click **Open Link →** to access external resources directly.
