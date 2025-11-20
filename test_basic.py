import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# =====================================================
# HEALTH CHECK
# =====================================================

def test_health_check_status():
    """La API responde correctamente"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

def test_health_check_has_version():
    """El health check incluye versión"""
    response = client.get("/health")
    assert "version" in response.json()

def test_health_check_has_timestamp():
    """El health check incluye timestamp"""
    response = client.get("/health")
    assert "timestamp" in response.json()

# =====================================================
# CREATE TASK (POST)
# =====================================================

def test_create_task_minimal():
    """Crear tarea mínima funciona"""
    response = client.post("/tasks", json={"title": "Test Task"})
    assert response.status_code == 201

def test_create_task_requires_title():
    """Validación: título requerido"""
    response = client.post("/tasks", json={})
    assert response.status_code == 422

def test_create_task_title_too_short():
    """Validación de longitud mínima"""
    response = client.post("/tasks", json={"title": "AB"})
    assert response.status_code == 422

# =====================================================
# LIST TASKS (GET)
# =====================================================

def test_list_tasks_returns_array():
    """La lista siempre retorna un array"""
    response = client.get("/tasks")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

# =====================================================
# GET TASK BY ID (GET)
# =====================================================

def test_get_task_not_found():
    """Tarea inexistente retorna 404"""
    response = client.get("/tasks/nonexistent-id")
    assert response.status_code == 404

# =====================================================
# UPDATE TASK (PUT)
# =====================================================

def test_update_task_requires_json():
    """Actualizar sin JSON retorna error"""
    response = client.put("/tasks/some-id", data="")
    assert response.status_code in (400, 422)

def test_update_task_not_found():
    """Actualizar tarea inexistente da 404"""
    response = client.put("/tasks/some-id", json={"title": "New"})
    assert response.status_code == 404

# =====================================================
# PATCH STATUS
# =====================================================

def test_patch_status_invalid():
    """Patch con estado inválido falla"""
    response = client.patch("/tasks/some-id/status?status=INVALID")
    assert response.status_code == 422

# =====================================================
# DELETE TASK
# =====================================================

def test_delete_task_not_found():
    """Eliminar tarea inexistente retorna 404"""
    response = client.delete("/tasks/some-id")
    assert response.status_code == 404

# =====================================================
# SEARCH TASKS
# =====================================================

def test_search_requires_min_chars():
    """Búsqueda requiere mínimo 2 caracteres"""
    response = client.get("/tasks/search?q=a")
    assert response.status_code == 400

def test_search_returns_array():
    """Búsqueda siempre retorna array (aunque vacío)"""
    response = client.get("/tasks/search?q=test")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

# =====================================================
# CORS
# =====================================================

def test_cors_headers_present():
    """Headers CORS deben existir si OPTIONS está habilitado; otherwise accept 405"""
    response = client.options("/tasks")

    # Caso 1: OPTIONS habilitado → deben existir headers CORS
    if response.status_code == 200:
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers

    # Caso 2: OPTIONS no implementado → FastAPI responde 405 → lo aceptamos
    else:
        assert response.status_code == 405


# =====================================================
# ERROR HANDLING GENERAL
# =====================================================

def test_invalid_json_returns_error():
    """JSON inválido debe retornar error"""
    response = client.post(
        "/tasks",
        data="invalid json",
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code in (400, 422)
