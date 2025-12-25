
from pathlib import Path

file_path = Path(r"d:\Download\Progetto WAR ROOM\warroom\backend\main.py")

endpoint_code = """

# --- REPORTS ---

@app.get("/api/reports/pdf")
def generate_pdf_report_endpoint():
    \"\"\"Generates and downloads a PDF report of the portfolio.\"\"\"
    try:
        from services.report_service import generate_pdf_report
        pdf_bytes = generate_pdf_report()
        if not pdf_bytes:
            raise HTTPException(status_code=500, detail="PDF Generation failed")
        
        filename = f"WarRoom_Report_{datetime.now().strftime('%Y%m%d')}.pdf"
        return Response(
            content=pdf_bytes, 
            media_type="application/pdf", 
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logger.error(f"Report Endpoint Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
"""

with open(file_path, "a", encoding="utf-8") as f:
    f.write(endpoint_code)

print("Endpoint appended successfully.")
