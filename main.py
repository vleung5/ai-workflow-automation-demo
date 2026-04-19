"""
Main entry point for the application
"""
import sys
import uvicorn

if __name__ == "__main__":
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║   AI Workflow Automation Demo                             ║
    ║   Async Pipeline for CSV Processing & AI Classification   ║
    ╚════════════════════════════════════════════════════════════╝
    """)
    
    print("Starting application on http://localhost:8000")
    print("Upload sample_data.csv to get started!\n")
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )