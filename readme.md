# My Resume API app

[https://cn-job-fit-scorer.azurewebsites.net/docs](https://cn-job-fit-scorer.azurewebsites.net/docs)

contact me if you need the API key.

## /extract-criteria

````python
file: UploadFile = File(..., description="Upload a PDF or DOCX file containing the job description"), 

additional_criteria: Optional[List[str]] = Form(None, description="Optional list of additional criteria to consider")): 
````

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

## /score-resumes

```python
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
        description="Optional job title to provide context for scoring (e.g., 'Flower Arranger', 'Head Chef'). This helps the AI better understand the domain and appropriate scoring benchmarks."````


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
```
