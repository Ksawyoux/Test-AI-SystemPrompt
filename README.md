# 🎯 Agentic Interviewer

AI-powered interview question generator using Google Gemini. Upload a resume and get tailored technical interview questions with scoring criteria.

## Features

- **Resume Analysis** - Extracts skills, experience, and domain expertise from PDF resumes
- **Job Description Generation** - Creates a relevant job description based on the candidate's profile
- **Smart Question Generation** - Produces 10 technical interview questions covering key competencies
- **Difficulty-Based Scoring**:
  - 🟢 Easy: 3-7 points
  - 🟠 Medium: 7-10 points
  - 🔴 Hard: 10-15 points
- **Scoring Criteria** - Each question includes guidance on what to look for in answers

## Quick Start

### 1. Clone and Install

```bash
cd Test_AI-SystemPrompt
pip install streamlit google-generativeai PyPDF2 python-dotenv
```

### 2. Set Up API Key

Get your Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey).

Edit the `.env` file:

```env
GEMINI_API_KEY=your_api_key_here
```

### 3. Run

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

## Usage

1. Upload a PDF resume
2. Wait for AI analysis (~10-20 seconds)
3. Review the generated job description
4. Go through each interview question
5. Use the scoring criteria to evaluate answers

## Tech Stack

- **Streamlit** - Web interface
- **Google Gemini 2.5 Flash** - AI model
- **PyPDF2** - PDF text extraction
- **python-dotenv** - Environment variable management

## Project Structure

```
Test_AI-SystemPrompt/
├── app.py          # Main application
├── .env            # API key (not committed)
└── README.md       # This file
```

## How It Works

1. **Phase 1: Context Analysis**
   - Parses resume content
   - Identifies technical skills and experience
   - Generates a matching job description

2. **Phase 2: Question Generation**
   - Extracts key competencies
   - Creates standardized interview questions
   - Assigns difficulty and points
   - Provides scoring rubrics

## License

MIT
