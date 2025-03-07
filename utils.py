#ultis.py 

import docx2txt
import PyPDF2
import io
from fastapi.responses import StreamingResponse
import pandas as pd

from fastapi import HTTPException

def extract_text(file_content, file_extension):
    """Extract text from PDF or DOCX files."""
    text = ""
    try:
        if file_extension.lower() == ".pdf":
            pdf_file = io.BytesIO(file_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            for page in pdf_reader.pages:
                text += page.extract_text()
        elif file_extension.lower() == ".docx":
            bytes_io = io.BytesIO(file_content)
            text = docx2txt.process(bytes_io)
        else:
            raise ValueError(f"Unsupported file format: {file_extension}")
        return text
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error extracting text: {str(e)}")



async def process_files(files):
        # Process all files upfront
    processed_files = []
    
    for file in files:
        # Check file extension
        file_extension = "." + file.filename.split(".")[-1]
        if file_extension.lower() not in [".pdf", ".docx"]:
            raise HTTPException(status_code=400, detail=f"File {file.filename} is not a supported format. Only PDF and DOCX files are supported")
        
        try:
            # Read file content
            file_content = await file.read()
            
            # Extract text from file
            resume_text = extract_text(file_content, file_extension)
            
            # Extract filename as fallback name
            fallback_name = file.filename.rsplit(".", 1)[0]
            
            processed_files.append({
                "filename": file.filename,
                "fallback_name": fallback_name,
                "resume_text": resume_text
            })
        except Exception as e:
            print(f"Error processing file {file.filename}: {str(e)}")
            # We could choose to add it with an error flag or skip it entirely
            processed_files.append({
                "filename": file.filename,
                "fallback_name": file.filename.rsplit(".", 1)[0],
                "resume_text": "",
                "error": f"Failed to process: {str(e)}"
            })
    return processed_files

def generate_excel_report(results):
    """
    Generate a formatted Excel report with summary and detailed analysis sheets.
    
    Args:
        results (list): List of dictionaries containing score results for each candidate
        
    Returns:
        StreamingResponse: Excel file as a streaming response
        
    Raises:
        HTTPException: If no valid results were generated or an error occurs
    """
    try:
        if not results:
            raise HTTPException(status_code=500, detail="No valid results were generated")
            
        # First, reorganize the data to separate scores and justifications
        summary_data = []
        detailed_data = []
        
        for result in results:
            if "Error" in result:
                # Handle error cases
                summary_row = {"Candidate": result["Candidate"], "Error": result["Error"]}
                summary_data.append(summary_row)
                detailed_data.append(result)
                continue
                
            # Extract candidate name and total score
            summary_row = {
                "Candidate": result["Candidate"],
                "Total Score": result.get("Total Score", 0)
            }
            
            detailed_row = {
                "Candidate": result["Candidate"]
            }
            
            # Process each criterion - separate scores for summary and keep justifications for details
            for key in result:
                if "(Score)" in key:
                    criterion = key.replace(" (Score)", "")
                    summary_row[criterion] = result[key]
                    
                    # Add both score and justification to detailed row
                    detailed_row[f"{criterion} - Score"] = result[key]
                    justification_key = f"{criterion} (Justification)"
                    if justification_key in result:
                        detailed_row[f"{criterion} - Justification"] = result[justification_key]
            
            summary_data.append(summary_row)
            detailed_data.append(detailed_row)
        
        # Create DataFrames
        summary_df = pd.DataFrame(summary_data)
        detailed_df = pd.DataFrame(detailed_data)
        
        # Sort by total score (descending)
        if "Total Score" in summary_df.columns:
            summary_df = summary_df.sort_values("Total Score", ascending=False)
            
        # Create Excel in memory with multiple sheets
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Add summary sheet
            summary_df.to_excel(writer, sheet_name="Summary Scores", index=False)
            
            # Add detailed sheet
            detailed_df.to_excel(writer, sheet_name="Detailed Analysis", index=False)
            
            # Get workbook and create format objects
            workbook = writer.book
            
            # Formats
            header_format = workbook.add_format({
                'bold': True,
                'font_color': 'white',
                'bg_color': '#4472C4',
                'border': 1,
                'align': 'center',
                'valign': 'vcenter',
            })
            
            score_format = workbook.add_format({
                'num_format': '0',
                'align': 'center',
                'border': 1,
            })
            
            candidate_format = workbook.add_format({
                'bold': True,
                'border': 1,
            })
            
            justification_format = workbook.add_format({
                'text_wrap': True,
                'valign': 'top',
                'border': 1,
            })
            
            # Format summary sheet
            summary_sheet = writer.sheets["Summary Scores"]
            
            # Format headers
            for col_num, value in enumerate(summary_df.columns.values):
                summary_sheet.write(0, col_num, value, header_format)
                
            # Format data
            for row_num in range(len(summary_df)):
                summary_sheet.write(row_num + 1, 0, summary_df.iloc[row_num, 0], candidate_format)
                
                for col_num in range(1, len(summary_df.columns)):
                    cell_value = summary_df.iloc[row_num, col_num]
                    if isinstance(cell_value, (int, float)) and "Score" in summary_df.columns[col_num]:
                        summary_sheet.write(row_num + 1, col_num, cell_value, score_format)
                    else:
                        summary_sheet.write(row_num + 1, col_num, cell_value)
            
            # Format detailed sheet
            detailed_sheet = writer.sheets["Detailed Analysis"]
            
            # Format headers
            for col_num, value in enumerate(detailed_df.columns.values):
                detailed_sheet.write(0, col_num, value, header_format)
                
            # Format data
            for row_num in range(len(detailed_df)):
                detailed_sheet.write(row_num + 1, 0, detailed_df.iloc[row_num, 0], candidate_format)
                
                for col_num in range(1, len(detailed_df.columns)):
                    cell_value = detailed_df.iloc[row_num, col_num]
                    if isinstance(cell_value, (int, float)) and "Score" in detailed_df.columns[col_num]:
                        detailed_sheet.write(row_num + 1, col_num, cell_value, score_format)
                    elif "Justification" in detailed_df.columns[col_num]:
                        detailed_sheet.write(row_num + 1, col_num, cell_value, justification_format)
                    else:
                        detailed_sheet.write(row_num + 1, col_num, cell_value)
            
            # Auto-adjust column widths
            for sheet in [summary_sheet, detailed_sheet]:
                for i, col in enumerate(sheet._df.columns if hasattr(sheet, '_df') else []):
                    # Set fixed width for score columns and wider for justification
                    if "Score" in col and "Total" not in col:
                        sheet.set_column(i, i, 10)
                    elif "Justification" in col:
                        sheet.set_column(i, i, 40)
                    elif col == "Candidate":
                        sheet.set_column(i, i, 20)
                    else:
                        # Dynamically size other columns
                        max_len = max(
                            sheet._df[col].astype(str).map(len).max() if hasattr(sheet, '_df') else 0,
                            len(str(col))
                        ) + 2
                        sheet.set_column(i, i, min(max_len, 30))  # Cap width at 30 characters
                        
            # Freeze the header row
            summary_sheet.freeze_panes(1, 0)
            detailed_sheet.freeze_panes(1, 0)
        
        output.seek(0)
        
        # Return Excel file
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=resume_scores.xlsx"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating Excel file: {str(e)}")