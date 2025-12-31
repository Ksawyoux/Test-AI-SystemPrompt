"""
Agentic Interviewer - AI-Powered Interview Question Generator
Uses Google Gemini AI to analyze resumes and generate tailored interview questions.
"""

import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
import json
import re
import csv
from io import StringIO
from typing import Optional, Tuple
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- CONSTANTS ---
MODEL_NAME = "gemini-2.5-flash"
MAX_QUESTIONS = 10

# Points per difficulty level
POINTS_RANGES = {
    "hard": (10, 15),
    "medium": (7, 10),
    "easy": (3, 7)
}

DIFFICULTY_COLORS = {
    "hard": "red",
    "medium": "orange",
    "easy": "green"
}

JD_TEMPLATE = """
**Job Title:** [Role Name]

**Company Information:**
Join a dynamic team at **[Company Name]**, a leader in innovative technology...

**Key Responsibilities:**
- [Responsibility 1]
- [Responsibility 2]
- [Responsibility 3]

**Qualifications:**
- [Qualification 1]
- [Qualification 2]
- [Qualification 3]

**Nice to Have:**
- [Optional Skill 1]
- [Optional Skill 2]
"""


# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Agentic Interviewer",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS ---
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 1rem;
        margin-bottom: 2rem;
        color: white;
        text-align: center;
    }
    .main-header h1 {
        margin: 0;
        font-size: 2.5rem;
    }
    .main-header p {
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
    }
</style>
""", unsafe_allow_html=True)


# --- HELPER FUNCTIONS ---
@st.cache_data
def extract_pdf_text(file_content: bytes) -> str:
    """Extract text content from a PDF file."""
    try:
        from io import BytesIO
        reader = PdfReader(BytesIO(file_content))
        text = "".join([page.extract_text() or "" for page in reader.pages])
        return text.strip()
    except Exception as e:
        st.error(f"Error reading PDF: {e}")
        return ""


def parse_questions_from_csv(raw_text: str) -> list[dict]:
    """
    Parse interview questions from CSV-style output.
    Handles quoted strings with commas and filters noise.
    """
    questions = []
    
    # Clean markdown code blocks
    clean_text = re.sub(r'```\w*\n?', '', raw_text).strip()
    
    # Extract only data lines (starting with a number)
    data_lines = []
    for line in clean_text.split('\n'):
        line = line.strip()
        if re.match(r'^\d+\s*,', line):
            data_lines.append(line)
    
    if not data_lines:
        return questions
    
    # Parse using CSV reader
    reader = csv.reader(StringIO('\n'.join(data_lines)), skipinitialspace=True)
    
    for row in reader:
        if len(row) >= 6:
            try:
                questions.append({
                    "id": int(row[0].strip()),
                    "title": row[1].strip().strip('"'),
                    "question_text": row[2].strip().strip('"'),
                    "difficulty": row[3].strip().strip('"'),
                    "max_points": int(row[4].strip()),
                    "scoring_criteria": row[5].strip().strip('"')
                })
            except (ValueError, IndexError) as e:
                st.warning(f"Skipped malformed row: {e}")
    
    return questions


def get_difficulty_color(difficulty: str) -> str:
    """Get color based on difficulty level."""
    return DIFFICULTY_COLORS.get(difficulty.lower(), "gray")


def display_question(q: dict, index: int) -> int:
    """Display a question card using native Streamlit components."""
    pts = q.get('max_points', 10)
    title = q.get('title', 'Topic')
    text = q.get('question_text', '...')
    diff = str(q.get('difficulty', 'Medium')).strip()
    criteria = q.get('scoring_criteria', 'No criteria provided')
    q_id = q.get('id', index + 1)
    
    # Simple color mapping
    diff_lower = diff.lower()
    if diff_lower == 'easy':
        color = 'green'
    elif diff_lower == 'hard':
        color = 'red'
    else:
        color = 'orange'
    
    # Simple layout with columns
    col1, col2 = st.columns([1, 6])
    
    with col1:
        st.markdown(f"### Q{q_id}")
        st.markdown(f":{color}[**{diff}**]")
        st.metric("Points", pts)
    
    with col2:
        st.markdown(f"**{title}**")
        st.info(text)
        with st.expander("Scoring Criteria"):
            st.write(criteria)
    
    st.divider()
    return pts


# --- AI CHAIN FUNCTIONS ---
def run_context_analysis(
    model: genai.GenerativeModel,
    resume_text: str
) -> Optional[dict]:
    """Phase 1: Analyze resume and generate context."""
    
    prompt = f"""
You are a Senior HR Analyst with expertise in technical recruiting.

INPUTS:
- RESUME: {resume_text}
- JD TEMPLATE: {JD_TEMPLATE}

TASK:
1. Analyze the candidate's persona based on their resume (skills, experience level, domain expertise).
2. Generate a generalized job description that matches their profile.
3. Create a campaign context summarizing the interview focus areas.
4. Do NOT describe the candidate.
5. Instead, describe the **skills and scenarios** that must be simulated to test a person for these roles.
6. Phrasing should be: "To simulate this job, the candidate must demonstrate..."

OUTPUT (JSON only, no markdown):
{{
    "campaign_context": "Brief summary of interview focus areas and the candidate general persona",
    "job_description": "Full markdown-formatted job description"
}}
"""
    
    try:
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        return json.loads(response.text)
    except json.JSONDecodeError as e:
        st.error(f"Failed to parse AI response: {e}")
        return None
    except Exception as e:
        st.error(f"Context analysis failed: {e}")
        return None


def run_question_generation(
    model: genai.GenerativeModel,
    context_data: dict
) -> list[dict]:
    """Phase 2: Generate interview questions."""
    
    prompt = f"""
You are an Expert Technical Interviewer.
Your goal is to create interview questions based on the core technical competencies required for a role.

INPUT CONTEXT:
{context_data.get('campaign_context', '')}
{context_data.get('job_description', '')}

INSTRUCTIONS:
1. Analyze the input to identify the key technical skills required.
2. Generalize these skills (e.g., if the resume says "Project Apollo API", use "RESTful API Design").
3. Generate exactly {MAX_QUESTIONS} interview questions covering distinct technical topics.
4. Include a mix of "Easy", "Medium", and "Hard" difficulty levels.
5. SCORING RULES:
   - Hard questions: 10-15 points
   - Medium questions: 7-10 points
   - Easy questions: 3-7 points
   - **CRITICAL: The total of all max_points MUST equal exactly 100.**

OUTPUT FORMAT (JSON only):
{{
    "questions": [
        {{
            "id": 1,
            "title": "Topic Name",
            "question_text": "The actual interview question to ask",
            "difficulty": "Easy",
            "max_points": 5,
            "scoring_criteria": "What to look for in a good answer"
        }}
    ]
}}
"""
    
    try:
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        data = json.loads(response.text)
        questions = data.get("questions", [])
        
        if not questions:
            st.warning("No questions generated. Raw AI output:")
            st.code(response.text, language="json")
        
        return questions
    except json.JSONDecodeError as e:
        st.error(f"Failed to parse AI response: {e}")
        st.code(response.text, language="text")
        return []
    except Exception as e:
        st.error(f"Question generation failed: {e}")
        return []


def run_agentic_chain(
    resume_text: str,
    api_key: str
) -> Tuple[Optional[dict], list[dict]]:
    """Execute the full agentic interview generation chain."""
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(MODEL_NAME)
    except Exception as e:
        st.error(f"Failed to initialize Gemini: {e}")
        return None, []
    
    # Phase 1: Context Analysis
    with st.status("🔍 Phase 1: Analyzing Resume & Context...", expanded=True) as status:
        st.write("Extracting candidate profile...")
        st.write("Generating job description...")
        
        context_data = run_context_analysis(model, resume_text)
        
        if context_data:
            status.update(label="✅ Phase 1 Complete", state="complete", expanded=False)
        else:
            status.update(label="❌ Phase 1 Failed", state="error")
            return None, []
    
    # Phase 2: Question Generation
    with st.status("📝 Phase 2: Generating Interview Questions...", expanded=True) as status:
        st.write(f"Creating {MAX_QUESTIONS} tailored questions...")
        st.write("Applying scoring criteria...")
        
        questions = run_question_generation(model, context_data)
        
        if questions:
            status.update(
                label=f"✅ Phase 2 Complete ({len(questions)} questions)",
                state="complete",
                expanded=False
            )
        else:
            status.update(label="❌ Phase 2 Failed", state="error")
    
    return context_data, questions


# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Settings")
    
    # Get API key from environment or user input
    env_api_key = os.getenv("GEMINI_API_KEY", "")
    
    if env_api_key:
        st.success("✅ API Key loaded from .env")
        api_key = env_api_key
    else:
        api_key = st.text_input(
            "Gemini API Key",
            type="password",
            help="Enter your Google Gemini API key"
        )
        if not api_key:
            st.info("💡 Add `GEMINI_API_KEY=your_key` to .env file")
    
    st.divider()
    
    st.markdown("### 📊 Model Info")
    st.markdown(f"**Model:** `{MODEL_NAME}`")
    st.markdown(f"**Questions:** {MAX_QUESTIONS}")
    st.markdown("**Scoring:** Easy 3-7, Medium 7-10, Hard 10-15")
    
    st.divider()
    
    st.markdown("### 📖 How to Use")
    st.markdown("""
    1. Upload a PDF resume
    2. Wait for AI analysis
    3. Review generated questions
    4. Use scoring guides for evaluation
    """)


# --- MAIN CONTENT ---
st.markdown("""
<div class="main-header">
    <h1>🎯 Agentic Interviewer</h1>
    <p>AI-powered interview question generator using Google Gemini</p>
</div>
""", unsafe_allow_html=True)

# File uploader
uploaded_file = st.file_uploader(
    "📄 Upload Resume (PDF)",
    type=["pdf"],
    help="Upload a candidate's resume to generate tailored interview questions"
)

# Process resume
if uploaded_file and api_key:
    # Use session state to cache results
    file_key = f"results_{uploaded_file.name}"
    
    if file_key not in st.session_state:
        resume_text = extract_pdf_text(uploaded_file.read())
        
        if resume_text:
            with st.spinner("Processing..."):
                context, questions = run_agentic_chain(resume_text, api_key)
                st.session_state[file_key] = {"context": context, "questions": questions}
        else:
            st.error("Could not extract text from PDF. Please try another file.")
            st.stop()
    
    # Get cached results
    cached = st.session_state.get(file_key, {})
    context = cached.get("context")
    questions = cached.get("questions", [])
    
    if context and questions:
        # Display results
        st.divider()
        
        # Job Description
        with st.expander("📄 Generated Job Description", expanded=False):
            st.markdown(context.get('job_description', 'No description available'))
        
        # Campaign Context
        with st.expander("🎯 Campaign Context", expanded=False):
            st.info(context.get('campaign_context', 'No context available'))
        
        st.divider()
        
        # Questions Header
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader(f"📝 Interview Questions ({len(questions)})")
        with col2:
            if st.button("🔄 Regenerate", help="Generate new questions"):
                if file_key in st.session_state:
                    del st.session_state[file_key]
                st.rerun()
        
        # Display questions
        total_score = 0
        for idx, q in enumerate(questions):
            total_score += display_question(q, idx)
        
        # Summary
        st.success(f"📊 **Total Exam Score: {total_score}/100 points**")

elif uploaded_file and not api_key:
    st.warning("⚠️ Please provide a Gemini API key in the sidebar or .env file")

else:
    # Simple welcome message
    st.markdown("""
    ### 👋 Welcome!
    
    Upload a PDF resume to get started. The AI will:
    
    1. **Analyze** the candidate's profile
    2. **Generate** a tailored job description
    3. **Create** 10 interview questions with scoring
    
    **Total: 100 points** 💯
    """)