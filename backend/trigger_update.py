from app.services.scores_service import update_scores_in_sheet
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    print("Triggering manual score update...")
    update_scores_in_sheet()
    print("Done.")
