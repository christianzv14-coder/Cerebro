from app.schemas import ActivityResponse
from app.models.models import Activity, ActivityState
from datetime import date

def test_schema_exclusion():
    # Create a dummy model instance with the secret fields populated
    db_activity = Activity(
        ticket_id="TEST-PRIVACY-1",
        fecha=date.today(),
        tecnico_nombre="Pedro Pascal",
        prioridad="ALTA SECRET",
        accesorios="GPS SECRET",
        comuna="SECRET CITY",
        region="SECRET REGION",
        estado=ActivityState.PENDIENTE
    )
    
    # Serialize using the Pydantic schema used by the API
    api_response = ActivityResponse.from_orm(db_activity)
    json_output = api_response.dict()
    
    print("Serialized JSON:", json_output)
    
    # Assert fields are NOT present
    forbidden_fields = ["prioridad", "accesorios", "comuna", "region"]
    errors = []
    
    for field in forbidden_fields:
        if field in json_output:
            errors.append(field)
            
    if errors:
        print(f"FAIL: The following fields leaked into the API schema: {errors}")
    else:
        print("SUCCESS: New fields are correctly hidden from the API/App.")

if __name__ == "__main__":
    test_schema_exclusion()
