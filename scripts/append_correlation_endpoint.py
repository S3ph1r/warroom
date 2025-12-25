
from pathlib import Path

file_path = Path(r"d:\Download\Progetto WAR ROOM\warroom\backend\main.py")

endpoint_code = """

@app.get("/api/analytics/correlation")
def get_correlation_matrix_endpoint():
    \"\"\"Get correlation matrix of top holdings.\"\"\"
    try:
        from services.analytics_service import calculate_correlation_matrix
        return calculate_correlation_matrix()
    except Exception as e:
        logger.error(f"Correlation Endpoint Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
"""

with open(file_path, "a", encoding="utf-8") as f:
    f.write(endpoint_code)

print("Correlation Endpoint appended successfully.")
