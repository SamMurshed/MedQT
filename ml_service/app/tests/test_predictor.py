from app.predictor import predict_wait_time


def test_prediction_structure() -> None:
    result = predict_wait_time(
        selected_symptoms=["fever"],
        queue_size=5,
    )

    assert "predicted_wait_minutes" in result
    assert "priority_score" in result

    predicted_wait = result["predicted_wait_minutes"]
    priority_score = result["priority_score"]

    assert isinstance(predicted_wait, float)
    assert isinstance(priority_score, float)

    assert predicted_wait >= 0.0
    assert 1.0 <= priority_score <= 10.0


def test_more_people_means_longer_wait_on_average() -> None:
    result_small_queue = predict_wait_time(
        selected_symptoms=["fever"],
        queue_size=2,
    )["predicted_wait_minutes"]

    result_large_queue = predict_wait_time(
        selected_symptoms=["fever"],
        queue_size=15,
    )["predicted_wait_minutes"]

    assert result_large_queue > result_small_queue


def test_urgent_symptoms_reduce_wait_time() -> None:
    mild_wait = predict_wait_time(
        selected_symptoms=["headache"],
        queue_size=10,
    )["predicted_wait_minutes"]

    urgent_wait = predict_wait_time(
        selected_symptoms=["chest_pain", "shortness_of_breath"],
        queue_size=10,
    )["predicted_wait_minutes"]

    assert urgent_wait < mild_wait
