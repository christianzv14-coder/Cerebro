import sys
import os
import logging

# Setup import path
sys.path.append(os.getcwd())

# Configure Logging to Console
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_sync():
    print(">>> STARTING LOCAL SYNC <<<")
    
    # Load env
    from dotenv import load_dotenv
    load_dotenv()
    
    try:
        from app.services.scores_service import update_scores_in_sheet
        update_scores_in_sheet()
        print(">>> SYNC COMPLETED <<<")
    except Exception as e:
        print(f">>> ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_sync()
