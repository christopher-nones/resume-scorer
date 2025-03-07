# app.py

from fastapi import FastAPI, File, UploadFile, Form, HTTPException,   Depends, Security
import json
import uvicorn
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.security.api_key import APIKeyHeader
from typing import List, Optional
import os

from utils import extract_text, process_files, generate_excel_report
from llm import LLM

# Load API key from environment variable (stored in Azure)
API_KEY = os.getenv("API_SECRET_KEY")

API_KEY = os.getenv("API_SECRET_KEY") or None
if API_KEY is None:
    raise RuntimeError("Missing API_SECRET_KEY")


# Define API key header
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# API Key validation function
def get_api_key(api_key: str = Security(api_key_header)):
    if not API_KEY:
        raise HTTPException(status_code=500, detail="API Key is missing. Get out of here you cheeky goose.")
    
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Unauthorized: Invalid API Key")
    
    return api_key


llm_analyzer = LLM()

app = FastAPI(
    title="Resume Scoring API",
    description="""
    This API provides tools to extract key criteria from job descriptions and score candidate 
    resumes against these criteria using AI.
    
    ## Features
    
    * Extract evaluation criteria from job descriptions
    * Score multiple resumes against extracted criteria
    * Generate detailed reports with justifications
    
    GitHub repository: https://github.com/christopher-nones/resume-scorer

    Use the API key I have provided.
    """,
    version="1.0.0",
    contact={
        "name": "Christopher Nones",
        "url": "https://github.com/christopher-nones"
    },
    openapi_url="/openapi.json",
    docs_url="/docs",  
    redoc_url="/redoc",
    debug=True
)

@app.post("/extract-criteria", response_model=dict, dependencies=[Depends(get_api_key)])
async def extract_job_criteria(
    file: UploadFile = File(..., description="Upload a PDF or DOCX file containing the job description"),
    additional_criteria: Optional[List[str]] = Form(None, description="Optional list of additional criteria to consider")):    
    """
    Extract key ranking criteria from a job description document.
    
    This endpoint analyzes the uploaded job description with an llm and extracts specific criteria that
    can be used to evaluate and score candidates. 
    
    Additional criteria is optional and is used by the llm to further refine the extracted criteria, either by adding to or modifying the critiera.
    
    - **file**: Upload a PDF or DOCX file containing the job description
    - **additional_criteria**: Optional list of additional criteria to consider
    
    **Example Response:**
    ```json
    {
      "criteria": [
        "Degree in Data Science, Computer Science, or related field",
        "Experience with Python programming",
        "Experience with SQL database querying",
        "Strong analytical skills"
      ]
    }
    ```
    """
    # Check file extension
    # Validate file extension using .endswith()
    filename_lower = (file.filename or "").lower()  

    if not file.filename.lower().endswith((".pdf", ".docx")):
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are supported")

    file_extension = filename_lower[filename_lower.rfind("."):]

    # Read file content
    file_content = await file.read()
    
    # Extract text from file
    job_description_text = extract_text(file_content, file_extension)

    system_prompt = "You are an expert HR specialist who scans job descriptions and resumes to extract information and score candidates."

    additional_criteria_text = ""
    if additional_criteria and len(additional_criteria) > 0:
        additional_criteria_formatted = "\n".join([f"- {criterion}" for criterion in additional_criteria])
        additional_criteria_text = f"""
        I have also included the following additional criteria that you should consider in your analysis. 
        You should integrate these with the criteria from the job description, and they may override or 
        complement the existing criteria:
        
        {additional_criteria_formatted}
        """
    
    prompt = f"""
    You are an expert HR recruiter tasked with extracting the key evaluation criteria from job descriptions.

    Your task is to identify the MOST IMPORTANT ranking criteria that would be used to evaluate and score candidates. Focus on extracting 5-12 KEY criteria that truly differentiate candidates for this role.

    IMPORTANT GUIDELINES:
    1. Focus on the CORE requirements of the role - what skills/qualifications are truly essential
    2. Keep different technologies separate (e.g., Python, SQL, AWS)
    3. Group related soft skills appropriately (don't create too many separate criteria)
    4. Include specific education/experience requirements as stated
    5. Prioritize technical skills and domain knowledge over generic abilities
    6. Avoid excessive granularity - too many criteria dilute the importance of each

    DO NOT include:
    - General job descriptions or responsibilities
    - Workplace benefits or policies
    - Physical work environment descriptions
    - Employment terms/conditions
    - Repetitive criteria that measure essentially the same skill

    Format your response as a JSON object with a single key 'criteria' that contains an array of strings, where each string is a separate criterion. List them in order of importance to the role.


    Examples of BAD criteria (too consolidated):
    - "Experience with Python, SQL, AWS, Excel, and PowerPoint"
    - "Strong communication and presentation skills"

    {additional_criteria_text}

    Here is the job description:

    {job_description_text}
    """
    try:
        
        llm_response = llm_analyzer.json_prompt(system_prompt,prompt)
        # Parse the JSON string into a Python dictionary
        if isinstance(llm_response, str):
            return json.loads(llm_response)
        return llm_response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"All LLM attempts failed: {str(e)}")
   

    
@app.post("/score-resumes", dependencies=[Depends(get_api_key)])
async def score_resumes(
    criteria: List[str] = Form(
        ..., 
        description="List of ranking criteria strings to evaluate candidates against. These should be specific skills, qualifications, or attributes that you want to score in each resume."
    ),
    files: List[UploadFile] = File(
        ..., 
        description="Upload multiple resume files in PDF or DOCX format. Each file will be analyzed separately against the provided criteria."
    ),
    job_title: Optional[str] = Form(
        None, 
        description="Optional job title to provide context for scoring (e.g., 'Flower Arranger', 'Head Chef'). This helps the AI better understand the domain and appropriate scoring benchmarks."
    )):
    """
    Score multiple resumes against the provided criteria.
    
    This endpoint analyzes each uploaded resume against the provided criteria and generates
    a detailed Excel report with scores and justifications for each candidate.
    
    - **criteria**: List of ranking criteria strings
    - **files**: List of resume files (PDF or DOCX)
    - **job_title**: Optional job title to provide context for scoring
    
    **Example Request:**
    - Form data with criteria like ["Python experience", "SQL experience", "Data Science degree"]
    - Multiple resume files uploaded
    - Optional job_title parameter (e.g., "Data Scientist")
    
    **Response:**
    An Excel file with two sheets:
    1. Summary Scores - Quick overview of all candidates and their scores
    2. Detailed Analysis - Complete breakdown with justifications for each score
    """
    if not criteria:
        raise HTTPException(status_code=400, detail="No criteria provided")
    
    if not files:
        raise HTTPException(status_code=400, detail="No resume files provided")
    
    # Load API configuration
    try:
        llm_analyzer = LLM()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading configuration: {str(e)}")
    
    # Format criteria for prompt
    criteria_formatted = "\n".join([f"- {c}" for c in criteria])

    processed_files = await process_files(files)
    
    # Analyze each resume only after all files are processed
    results = []
    
    for processed_file in processed_files:
        # Skip files with processing errors
        if "error" in processed_file:
            results.append({
                "Candidate": processed_file["fallback_name"],
                "Error": processed_file["error"]
            })
            continue
            
        # Prepare prompt for LLM
        job_context = f"for a {job_title} position" if job_title else "for this position"
        
        prompt = f"""
        You are a technical recruiter evaluating candidates {job_context}. Analyze the provided resume against the following job criteria.

        For each criterion, assign a score from 0 to 5 where:
        - 0: No evidence of the criterion in the resume
        - 1: Minimal/indirect evidence or very weak match
        - 2: Some evidence but limited or tangential experience/qualification
        - 3: Moderate evidence showing relevant experience/qualification
        - 4: Strong evidence of meeting the criterion with substantial experience
        - 5: Excellent match, exceeding the criterion requirements with extensive experience

        CRITICAL SCORING GUIDELINES:
        1. The most important criteria for this role are directly related to the core technical and domain requirements of {job_title if job_title else "the role"}
        2. Candidates without direct experience in the primary domain of {job_title if job_title else "the role"} should receive substantially lower overall scores
        3. Generic transferable skills (like "communication") should not compensate for a lack of core technical requirements
        4. Secondary or "nice to have" skills should not significantly impact the total score compared to essential skills
        5. Require EXPLICIT evidence in the resume - do not assume skills based on job titles alone
        6. For technical skills, look for specific mentions and practical application

        Format your response as a JSON object with the candidate name and an array of scores, where each score is an object with the criterion and score value.

        Here are the criteria:
        {criteria_formatted}

        Here is the resume text:
        {processed_file["resume_text"]}

        Example Output:
        {{
        "candidate_name": "John Doe",
        "scores": [
            {{
            "criterion": "Experience with Python programming",
            "score": 5,
            "justification": "The candidate has 5+ years of Python development with specific projects including ML model development and data pipelines."
            }},
            {{
            "criterion": "Experience with AWS cloud services",
            "score": 0,
            "justification": "No mention of AWS experience anywhere in the resume."
            }}
        ]
        }}
        """
        
        # Get scores from LLM
        try:
            # Enhanced system prompt that includes job title context
            system_prompt = f"You are an expert technical recruiter specialized in evaluating candidates for {job_title if job_title else 'technical'} roles."
            
            # Get the JSON string response from the LLM
            json_response = llm_analyzer.json_prompt(system_prompt, prompt)
            print(f"Received response for {processed_file['filename']}")
            
            # Parse the JSON string to a Python dictionary
            criteria_data = json.loads(json_response)
            
            # Validate response format
            if not isinstance(criteria_data, dict):
                raise ValueError("LLM response is not in the expected format")
            
            # Use the name extracted by the LLM, or fall back to the filename
            llm_extracted_name = criteria_data.get("candidate_name", "")
            candidate_result = {
                "Candidate": llm_extracted_name if llm_extracted_name else processed_file["fallback_name"]
            }
            
            # Extract scores for each criterion
            total_score = 0
            for score_item in criteria_data.get("scores", []):
                criterion = score_item.get("criterion", "Unknown")
                score = score_item.get("score", 0)
                justification = score_item.get("justification", "")
                
                candidate_result[f"{criterion} (Score)"] = score
                candidate_result[f"{criterion} (Justification)"] = justification
                total_score += score
            
            candidate_result["Total Score"] = total_score
            results.append(candidate_result)
            
        except Exception as e:
            # Log the error but continue processing other resumes
            print(f"Error analyzing {processed_file['filename']}: {str(e)}")
            # Add a placeholder result with error information
            results.append({
                "Candidate": processed_file["fallback_name"],
                "Error": f"Failed to analyze: {str(e)}"
            })
    
    # Generate Excel report
    return generate_excel_report(results)        
        
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,  
        title=app.title,
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@3/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@3/swagger-ui.css",
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)