import pytest
from fastapi.testclient import TestClient
from src.server import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["agent"] == "BaseRootAgent"
    assert "model" in data

def test_chat_rest_endpoint_success():
    payload = {
        "message": "Bom dia",
        "user_id": "test_user_rest",
        "session_id": None
    }
    response = client.post("/api/v1/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert "response" in data
    assert len(data["response"]) > 0
    assert data["user_id"] == "test_user_rest"
    assert "session_id" in data
    
    metrics = data["metrics"]
    assert metrics["prompt_tokens"] > 0
    assert metrics["total_tokens"] > metrics["prompt_tokens"]
    assert metrics["latency_ms"] > 0
    assert "ALTO_CONSUMO_TOKENS_SAUDACAO (Prompt Bloqueado enviado inteiro)" in metrics["problem_tags"]

def test_chat_rest_endpoint_empty_message():
    payload = {
        "message": "   ",
        "user_id": "test_user_empty"
    }
    response = client.post("/api/v1/chat", json=payload)
    assert response.status_code == 400

def test_chat_websocket_endpoint_streaming():
    with client.websocket_connect("/ws/chat") as websocket:
        websocket.send_json({
            "message": "Quem é a empresa?",
            "user_id": "test_user_ws"
        })
        
        events = []
        # Aguarda eventos até receber 'complete'
        while True:
            data = websocket.receive_json()
            events.append(data)
            if data.get("type") == "complete":
                break
        
        event_types = [e.get("type") for e in events]
        assert "start" in event_types
        assert "complete" in event_types
        
        final_event = events[-1]
        assert final_event["type"] == "complete"
        assert len(final_event["text"]) > 0
        assert final_event["metrics"]["total_tokens"] > 0
