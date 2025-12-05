from typing import List, Dict, Any

from bson import ObjectId

from app.database import get_database
from app.services.ml_client import request_wait_time_prediction


async def create_appointment_for_patient(
    patient_id: ObjectId,
    symptom_names: List[str],
) -> Dict[str, Any]:
    """
    Create a new appointment in the queue for a patient and call ML service
    to estimate wait time.

    Returns the inserted appointment document (including queue_number and
    predicted_wait_minutes).
    """
    database = get_database()
    appointment_collection = database["appointments"]

    # How many patients are already waiting?
    waiting_count = await appointment_collection.count_documents({"status": "waiting"})
    queue_number = waiting_count + 1
    queue_size_for_model = queue_number

    ml_prediction = await request_wait_time_prediction(
        symptom_names=symptom_names,
        queue_size=queue_size_for_model,
    )

    appointment_document: Dict[str, Any] = {
        "patient_id": patient_id,
        "symptoms": symptom_names,
        "status": "waiting",
        "queue_number": queue_number,
        "predicted_wait_minutes": ml_prediction["predicted_wait_minutes"],
        "priority_score": ml_prediction["priority_score"],
    }

    insert_result = await appointment_collection.insert_one(appointment_document)
    appointment_document["_id"] = insert_result.inserted_id

    return appointment_document
