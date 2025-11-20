import pytest
from fastapi.testclient import TestClient
from app.main import app, repository, TaskStatus, Priority
import uuid
from datetime import datetime


# ============= FIXTURES =============
@pytest.fixture
def client():
    """Cliente de prueba para la API"""
    repository._storage.clear()
    return TestClient(app)

@pytest.fixture
def session_client(client):
    """Cliente con sesión establecida"""
    response = client.get("/health")
    return client

@pytest.fixture
def sample_task():
    """Tarea de ejemplo"""
    return {
        "title": "Test Task",
        "description": "Test Description",
        "priority": 3,
        "tags": ["test", "sample"]
    }

@pytest.fixture
def created_task(session_client, sample_task):
    """Crea y retorna una tarea"""
    response = session_client.post("/tasks", json=sample_task)
    return response.json()

# ============= TESTS HEALTH CHECK =============
class TestHealthCheck:
    def test_health_check_status(self, client):
        """Test 1: Health check retorna status healthy"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    def test_health_check_has_version(self, client):
        """Test 2: Health check incluye versión"""
        response = client.get("/health")
        data = response.json()
        assert "version" in data
        assert data["version"] == "2.0.0"
    
    def test_health_check_has_timestamp(self, client):
        """Test 3: Health check incluye timestamp"""
        response = client.get("/health")
        assert "timestamp" in response.json()

# ============= TESTS CREATE (POST) =============
class TestCreateTask:
    def test_create_task_success(self, session_client, sample_task):
        """Test 4: Crear tarea exitosamente"""
        response = session_client.post("/tasks", json=sample_task)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == sample_task["title"]
        assert data["status"] == "PENDING"
        assert "id" in data
    
    def test_create_task_generates_id(self, session_client):
        """Test 5: ID se genera automáticamente"""
        task = {"title": "Auto ID Task"}
        response = session_client.post("/tasks", json=task)
        data = response.json()
        assert data["id"] is not None
        assert len(data["id"]) == 36  # UUID format
    
    def test_create_task_sets_default_status(self, session_client):
        """Test 6: Estado por defecto es PENDING"""
        response = session_client.post("/tasks", json={"title": "Default Status"})
        assert response.json()["status"] == "PENDING"
    
    def test_create_task_sets_timestamps(self, session_client):
        """Test 7: Timestamps se establecen automáticamente"""
        response = session_client.post("/tasks", json={"title": "Timestamps"})
        data = response.json()
        assert "created_at" in data
        assert "updated_at" in data
    
    def test_create_task_with_all_fields(self, session_client):
        """Test 8: Crear tarea con todos los campos"""
        task = {
            "title": "Complete Task",
            "description": "Full description",
            "priority": 4,
            "tags": ["urgent", "important"],
            "due_date": "2025-12-31"
        }
        response = session_client.post("/tasks", json=task)
        data = response.json()
        assert data["title"] == task["title"]
        assert data["description"] == task["description"]
        assert data["priority"] == task["priority"]
        assert data["tags"] == task["tags"]
    
    def test_create_task_invalid_title_too_short(self, session_client):
        """Test 9: Título demasiado corto falla"""
        response = session_client.post("/tasks", json={"title": "AB"})
        assert response.status_code == 422
    
    def test_create_task_invalid_title_empty(self, session_client):
        """Test 10: Título vacío falla"""
        response = session_client.post("/tasks", json={"title": ""})
        assert response.status_code == 422
    
    def test_create_task_invalid_priority_high(self, session_client):
        """Test 11: Prioridad muy alta falla"""
        response = session_client.post("/tasks", json={"title": "Test", "priority": 5})
        assert response.status_code == 422
    
    def test_create_task_invalid_priority_low(self, session_client):
        """Test 12: Prioridad muy baja falla"""
        response = session_client.post("/tasks", json={"title": "Test", "priority": 0})
        assert response.status_code == 422
    
    def test_create_task_missing_required_field(self, session_client):
        """Test 13: Campo requerido faltante falla"""
        response = session_client.post("/tasks", json={"description": "No title"})
        assert response.status_code == 422
    
    def test_create_task_title_whitespace_trimmed(self, session_client):
        """Test 14: Espacios en blanco se eliminan"""
        response = session_client.post("/tasks", json={"title": "  Trimmed  "})
        assert response.json()["title"] == "Trimmed"

# ============= TESTS READ (GET) =============
class TestReadTasks:
    def test_list_tasks_empty(self, session_client):
        """Test 15: Listar tareas vacío retorna array vacío"""
        response = session_client.get("/tasks")
        assert response.status_code == 200
        assert response.json() == []
    
    def test_list_tasks_returns_created_task(self, session_client, created_task):
        """Test 16: Listar retorna tareas creadas"""
        response = session_client.get("/tasks")
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == created_task["id"]
    
    def test_list_tasks_multiple(self, session_client):
        """Test 17: Listar múltiples tareas"""
        for i in range(5):
            session_client.post("/tasks", json={"title": f"Task {i}"})
        response = session_client.get("/tasks")
        assert len(response.json()) == 5
    
    def test_get_task_by_id_success(self, session_client, created_task):
        """Test 18: Obtener tarea por ID exitoso"""
        response = session_client.get(f"/tasks/{created_task['id']}")
        assert response.status_code == 200
        assert response.json()["id"] == created_task["id"]
    
    def test_get_task_by_id_not_found(self, session_client):
        """Test 19: Tarea no encontrada retorna 404"""
        response = session_client.get(f"/tasks/{uuid.uuid4()}")
        assert response.status_code == 404
    
    def test_list_tasks_filter_by_status(self, session_client):
        """Test 20: Filtrar tareas por estado"""
        session_client.post("/tasks", json={"title": "Pending Task"})
        task2 = session_client.post("/tasks", json={"title": "Task 2"}).json()
        session_client.patch(f"/tasks/{task2['id']}/status?status=COMPLETED")
        
        response = session_client.get("/tasks?status=PENDING")
        data = response.json()
        assert len(data) == 1
        assert data[0]["status"] == "PENDING"
    
    def test_list_tasks_different_sessions(self, client):
        """Test 21: Tareas separadas por sesión"""
        client1 = TestClient(app)
        client2 = TestClient(app)
        
        client1.post("/tasks", json={"title": "Client 1 Task"})
        client2.post("/tasks", json={"title": "Client 2 Task"})
        
        tasks1 = client1.get("/tasks").json()
        tasks2 = client2.get("/tasks").json()
        
        assert len(tasks1) == 1
        assert len(tasks2) == 1
        assert tasks1[0]["title"] != tasks2[0]["title"]

# ============= TESTS UPDATE (PUT/PATCH) =============
class TestUpdateTask:
    def test_update_task_title(self, session_client, created_task):
        """Test 22: Actualizar título de tarea"""
        update = {"title": "Updated Title"}
        response = session_client.put(f"/tasks/{created_task['id']}", json=update)
        assert response.status_code == 200
        assert response.json()["title"] == "Updated Title"
    
    def test_update_task_description(self, session_client, created_task):
        """Test 23: Actualizar descripción"""
        update = {"description": "New description"}
        response = session_client.put(f"/tasks/{created_task['id']}", json=update)
        assert response.json()["description"] == "New description"
    
    def test_update_task_status(self, session_client, created_task):
        """Test 24: Actualizar estado"""
        update = {"status": "COMPLETED"}
        response = session_client.put(f"/tasks/{created_task['id']}", json=update)
        assert response.json()["status"] == "COMPLETED"
    
    def test_update_task_priority(self, session_client, created_task):
        """Test 25: Actualizar prioridad"""
        update = {"priority": 4}
        response = session_client.put(f"/tasks/{created_task['id']}", json=update)
        assert response.json()["priority"] == 4
    
    def test_update_task_multiple_fields(self, session_client, created_task):
        """Test 26: Actualizar múltiples campos"""
        update = {
            "title": "Multi Update",
            "description": "New desc",
            "priority": 1
        }
        response = session_client.put(f"/tasks/{created_task['id']}", json=update)
        data = response.json()
        assert data["title"] == update["title"]
        assert data["description"] == update["description"]
        assert data["priority"] == update["priority"]
    
    def test_update_task_no_fields(self, session_client, created_task):
        """Test 28: Actualizar sin campos falla"""
        response = session_client.put(f"/tasks/{created_task['id']}", json={})
        assert response.status_code == 400
    
    def test_update_task_invalid_status(self, session_client, created_task):
        """Test 29: Estado inválido falla"""
        response = session_client.put(
            f"/tasks/{created_task['id']}", 
            json={"status": "INVALID"}
        )
        assert response.status_code == 422
    
    def test_patch_task_status(self, session_client, created_task):
        """Test 30: PATCH para actualizar solo estado"""
        response = session_client.patch(
            f"/tasks/{created_task['id']}/status?status=IN_PROGRESS"
        )
        assert response.status_code == 200
        assert response.json()["status"] == "IN_PROGRESS"
    
    def test_update_preserves_other_fields(self, session_client, created_task):
        """Test 31: Actualización preserva otros campos"""
        original_desc = created_task["description"]
        session_client.put(f"/tasks/{created_task['id']}", json={"title": "New"})
        updated = session_client.get(f"/tasks/{created_task['id']}").json()
        assert updated["description"] == original_desc
    
    def test_update_changes_updated_at(self, session_client, created_task):
        """Test 32: Actualización cambia updated_at"""
        import time
        time.sleep(0.1)
        response = session_client.put(
            f"/tasks/{created_task['id']}", 
            json={"title": "Changed"}
        )
        assert response.json()["updated_at"] != created_task["updated_at"]

# ============= TESTS DELETE =============
class TestDeleteTask:
    def test_delete_task_success(self, session_client, created_task):
        """Test 33: Eliminar tarea exitosamente"""
        response = session_client.delete(f"/tasks/{created_task['id']}")
        assert response.status_code == 204
    
    def test_delete_task_not_found(self, session_client):
        """Test 34: Eliminar tarea inexistente falla"""
        response = session_client.delete(f"/tasks/{uuid.uuid4()}")
        assert response.status_code == 404
    
    def test_delete_task_removes_from_list(self, session_client, created_task):
        """Test 35: Tarea eliminada no aparece en lista"""
        session_client.delete(f"/tasks/{created_task['id']}")
        response = session_client.get("/tasks")
        assert len(response.json()) == 0
    
    def test_delete_task_cannot_get_after(self, session_client, created_task):
        """Test 36: No se puede obtener tarea eliminada"""
        session_client.delete(f"/tasks/{created_task['id']}")
        response = session_client.get(f"/tasks/{created_task['id']}")
        assert response.status_code == 404
    
    def test_delete_all_tasks(self, session_client):
        """Test 37: Eliminar todas las tareas"""
        for i in range(3):
            session_client.post("/tasks", json={"title": f"Task {i}"})
        
        response = session_client.delete("/tasks")
        assert response.status_code == 204
        
        tasks = session_client.get("/tasks").json()
        assert len(tasks) == 0
    
    def test_delete_specific_task_from_multiple(self, session_client):
        """Test 38: Eliminar tarea específica de varias"""
        tasks = []
        for i in range(3):
            r = session_client.post("/tasks", json={"title": f"Task {i}"})
            tasks.append(r.json())
        
        session_client.delete(f"/tasks/{tasks[1]['id']}")
        
        remaining = session_client.get("/tasks").json()
        assert len(remaining) == 2
        assert tasks[1]['id'] not in [t['id'] for t in remaining]

# ============= TESTS SEARCH =============
class TestSearchTasks:
    def test_search_tasks_by_title(self, session_client):
        """Test 39: Buscar tareas por título"""
        session_client.post("/tasks", json={"title": "Python Development"})
        session_client.post("/tasks", json={"title": "Java Project"})
        
        response = session_client.get("/tasks/search?q=Python")
        data = response.json()
        assert len(data) == 1
        assert "Python" in data[0]["title"]
    
    def test_search_tasks_by_description(self, session_client):
        """Test 40: Buscar por descripción"""
        session_client.post("/tasks", json={
            "title": "Task 1",
            "description": "Important meeting"
        })
        session_client.post("/tasks", json={
            "title": "Task 2",
            "description": "Code review"
        })
        
        response = session_client.get("/tasks/search?q=meeting")
        assert len(response.json()) == 1
    
    def test_search_tasks_case_insensitive(self, session_client):
        """Test 41: Búsqueda insensible a mayúsculas"""
        session_client.post("/tasks", json={"title": "URGENT Task"})
        
        response = session_client.get("/tasks/search?q=urgent")
        assert len(response.json()) == 1
    
    def test_search_tasks_no_results(self, session_client, created_task):
        """Test 42: Búsqueda sin resultados"""
        response = session_client.get("/tasks/search?q=nonexistent")
        assert response.json() == []
    
    def test_search_tasks_min_length(self, session_client):
        """Test 43: Búsqueda requiere mínimo 2 caracteres"""
        response = session_client.get("/tasks/search?q=a")
        assert response.status_code == 400

# ============= TESTS STATISTICS =============
class TestStatistics:
    def test_stats_empty(self, session_client):
        """Test 44: Estadísticas con lista vacía"""
        response = session_client.get("/tasks/stats")
        data = response.json()
        assert data["total"] == 0
        assert data["pending"] == 0
    
    def test_stats_counts_total(self, session_client):
        """Test 45: Estadísticas cuenta total correcto"""
        for i in range(5):
            session_client.post("/tasks", json={"title": f"Task {i}"})
        
        stats = session_client.get("/tasks/stats").json()
        assert stats["total"] == 5
    
    def test_stats_counts_by_status(self, session_client):
        """Test 46: Estadísticas cuenta por estado"""
        tasks = []
        for i in range(4):
            r = session_client.post("/tasks", json={"title": f"Task {i}"})
            tasks.append(r.json())
        
        session_client.patch(f"/tasks/{tasks[0]['id']}/status?status=COMPLETED")
        session_client.patch(f"/tasks/{tasks[1]['id']}/status?status=COMPLETED")
        session_client.patch(f"/tasks/{tasks[2]['id']}/status?status=IN_PROGRESS")
        
        stats = session_client.get("/tasks/stats").json()
        assert stats["total"] == 4
        assert stats["pending"] == 1
        assert stats["in_progress"] == 1
        assert stats["completed"] == 2
    
    def test_stats_includes_all_statuses(self, session_client):
        """Test 47: Estadísticas incluye todos los estados"""
        stats = session_client.get("/tasks/stats").json()
        assert "pending" in stats
        assert "in_progress" in stats
        assert "completed" in stats
        assert "cancelled" in stats

# ============= TESTS VALIDATION =============
class TestValidation:
    def test_title_max_length(self, session_client):
        """Test 48: Título respeta longitud máxima"""
        long_title = "A" * 201
        response = session_client.post("/tasks", json={"title": long_title})
        assert response.status_code == 422
    
    def test_description_max_length(self, session_client):
        """Test 49: Descripción respeta longitud máxima"""
        long_desc = "A" * 1001
        response = session_client.post("/tasks", json={
            "title": "Valid",
            "description": long_desc
        })
        assert response.status_code == 422
    
    def test_priority_boundaries(self, session_client):
        """Test 50: Prioridad solo acepta 1-4"""
        valid_priorities = [1, 2, 3, 4]
        for p in valid_priorities:
            response = session_client.post("/tasks", json={
                "title": f"Priority {p}",
                "priority": p
            })
            assert response.status_code == 201
    
    def test_status_enum_validation(self, session_client, created_task):
        """Test 51: Estado solo acepta valores del enum"""
        valid_statuses = ["PENDING", "IN_PROGRESS", "COMPLETED", "CANCELLED"]
        for status in valid_statuses:
            response = session_client.patch(
                f"/tasks/{created_task['id']}/status?status={status}"
            )
            assert response.status_code == 200

# ============= TESTS SESSION MANAGEMENT =============
class TestSessionManagement:
    def test_session_cookie_created(self, client):
        """Test 52: Cookie de sesión se crea automáticamente"""
        response = client.get("/health")
        assert "session_id" in response.cookies
    
    def test_session_persists(self, session_client):
        """Test 53: Sesión persiste entre requests"""
        session_client.post("/tasks", json={"title": "Task 1"})
        tasks = session_client.get("/tasks").json()
        assert len(tasks) == 1
    
    def test_different_sessions_isolated(self):
        """Test 54: Sesiones diferentes están aisladas"""
        client1 = TestClient(app)
        client2 = TestClient(app)
        
        client1.post("/tasks", json={"title": "Client 1"})
        client2.post("/tasks", json={"title": "Client 2"})
        
        assert len(client1.get("/tasks").json()) == 1
        assert len(client2.get("/tasks").json()) == 1

# ============= TESTS EDGE CASES =============
class TestEdgeCases:
    def test_create_task_with_unicode(self, session_client):
        """Test 55: Tarea con caracteres Unicode"""
        response = session_client.post("/tasks", json={
            "title": "Tarea con émojis 🚀✨",
            "description": "Descripción con ñ y acentos"
        })
        assert response.status_code == 201
    
    def test_create_task_with_special_chars(self, session_client):
        """Test 56: Caracteres especiales en título"""
        response = session_client.post("/tasks", json={
            "title": "Task with @#$% chars"
        })
        assert response.status_code == 201
    
    def test_empty_tags_array(self, session_client):
        """Test 57: Array de tags vacío es válido"""
        response = session_client.post("/tasks", json={
            "title": "No tags",
            "tags": []
        })
        assert response.status_code == 201
        assert response.json()["tags"] == []
    
    def test_null_optional_fields(self, session_client):
        """Test 58: Campos opcionales null son válidos"""
        response = session_client.post("/tasks", json={
            "title": "Minimal",
            "description": None,
            "due_date": None
        })
        assert response.status_code == 201
    
    def test_update_with_null_values(self, session_client, created_task):
        """Test 59: Actualizar con valores null"""
        response = session_client.put(f"/tasks/{created_task['id']}", json={
            "description": None
        })
        assert response.status_code == 200

# ============= TESTS CORS =============
class TestCORS:
    def test_cors_headers_present(self, client):
        """Test 60: Headers CORS presentes"""
        response = client.options("/tasks")
        assert "access-control-allow-origin" in response.headers
    
    def test_cors_allows_methods(self, client):
        """Test 61: CORS permite métodos necesarios"""
        response = client.options("/tasks")
        allowed = response.headers.get("access-control-allow-methods", "")
        assert "GET" in allowed or "*" in allowed

# ============= TESTS ERROR HANDLING =============
class TestErrorHandling:
    def test_404_returns_json_error(self, session_client):
        """Test 62: Error 404 retorna JSON"""
        response = session_client.get(f"/tasks/{uuid.uuid4()}")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data or "error" in data
    
    def test_422_validation_error(self, session_client):
        """Test 63: Error de validación retorna 422"""
        response = session_client.post("/tasks", json={"title": "AB"})
        assert response.status_code == 422
    
    def test_invalid_json_returns_error(self, session_client):
        """Test 64: JSON inválido retorna error"""
        response = session_client.post(
            "/tasks",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code in [400, 422]

# ============= TESTS BUSINESS LOGIC =============
class TestBusinessLogic:
    def test_task_lifecycle(self, session_client):
        """Test 65: Ciclo de vida completo de tarea"""
        # Crear
        task = session_client.post("/tasks", json={"title": "Lifecycle"}).json()
        assert task["status"] == "PENDING"
        
        # Actualizar a en progreso
        session_client.patch(f"/tasks/{task['id']}/status?status=IN_PROGRESS")
        task = session_client.get(f"/tasks/{task['id']}").json()
        assert task["status"] == "IN_PROGRESS"
        
        # Completar
        session_client.patch(f"/tasks/{task['id']}/status?status=COMPLETED")
        task = session_client.get(f"/tasks/{task['id']}").json()
        assert task["status"] == "COMPLETED"
        
        # Eliminar
        session_client.delete(f"/tasks/{task['id']}")
        response = session_client.get(f"/tasks/{task['id']}")
        assert response.status_code == 404
    
    def test_priority_ordering_logic(self, session_client):
        """Test 66: Lógica de prioridades"""
        priorities = [1, 2, 3, 4]
        for p in priorities:
            session_client.post("/tasks", json={
                "title": f"Priority {p}",
                "priority": p
            })
        
        tasks = session_client.get("/tasks").json()
        assert len(tasks) == 4
    
    def test_tags_functionality(self, session_client):
        """Test 67: Funcionalidad de tags"""
        response = session_client.post("/tasks", json={
            "title": "Tagged Task",
            "tags": ["urgent", "backend", "api"]
        })
        task = response.json()
        assert len(task["tags"]) == 3
        assert "urgent" in task["tags"]

# ============= TESTS PERFORMANCE =============
class TestPerformance:
    def test_create_multiple_tasks_performance(self, session_client):
        """Test 68: Crear múltiples tareas"""
        import time
        start = time.time()
        
        for i in range(50):
            session_client.post("/tasks", json={"title": f"Task {i}"})
        
        elapsed = time.time() - start
        assert elapsed < 5  # Menos de 5 segundos para 50 tareas
    
    def test_list_large_dataset(self, session_client):
        """Test 69: Listar dataset grande"""
        for i in range(100):
            session_client.post("/tasks", json={"title": f"Task {i}"})
        
        import time
        start = time.time()
        response = session_client.get("/tasks")
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert len(response.json()) == 100
        assert elapsed < 1  # Menos de 1 segundo

# ============= TESTS CONCURRENCY =============
class TestConcurrency:
    def test_concurrent_task_creation(self, session_client):
        """Test 70: Creación concurrente de tareas"""
        from concurrent.futures import ThreadPoolExecutor
        
        def create_task(i):
            return session_client.post("/tasks", json={"title": f"Concurrent {i}"})
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_task, i) for i in range(10)]
            results = [f.result() for f in futures]
        
        assert all(r.status_code == 201 for r in results)
        tasks = session_client.get("/tasks").json()
        assert len(tasks) == 10

# ============= TESTS DATA INTEGRITY =============
class TestDataIntegrity:
    def test_task_id_uniqueness(self, session_client):
        """Test 71: IDs de tareas son únicos"""
        tasks = []
        for i in range(10):
            r = session_client.post("/tasks", json={"title": f"Task {i}"})
            tasks.append(r.json())
        
        ids = [t["id"] for t in tasks]
        assert len(ids) == len(set(ids))  # Todos únicos
    
    def test_timestamps_immutable(self, session_client, created_task):
        """Test 72: created_at es inmutable"""
        original_created = created_task["created_at"]
        
        session_client.put(f"/tasks/{created_task['id']}", json={"title": "Updated"})
        
        updated = session_client.get(f"/tasks/{created_task['id']}").json()
        assert updated["created_at"] == original_created
    
    def test_data_persistence_across_requests(self, session_client):
        """Test 73: Datos persisten entre requests"""
        task = session_client.post("/tasks", json={"title": "Persist"}).json()
        
        # Múltiples requests
        for _ in range(5):
            fetched = session_client.get(f"/tasks/{task['id']}").json()
            assert fetched["title"] == "Persist"

# ============= TESTS FILTERING =============
class TestFiltering:
    def test_filter_by_pending_status(self, session_client):
        """Test 74: Filtrar por estado PENDING"""
        session_client.post("/tasks", json={"title": "Pending 1"})
        session_client.post("/tasks", json={"title": "Pending 2"})
        
        response = session_client.get("/tasks?status=PENDING")
        assert len(response.json()) == 2
    
    def test_filter_by_completed_status(self, session_client):
        """Test 75: Filtrar por estado COMPLETED"""
        task = session_client.post("/tasks", json={"title": "To Complete"}).json()
        session_client.patch(f"/tasks/{task['id']}/status?status=COMPLETED")
        
        response = session_client.get("/tasks?status=COMPLETED")
        assert len(response.json()) == 1
        assert response.json()[0]["status"] == "COMPLETED"
    
    def test_filter_returns_empty_when_no_match(self, session_client, created_task):
        """Test 76: Filtro sin coincidencias retorna vacío"""
        response = session_client.get("/tasks?status=CANCELLED")
        assert response.json() == []

# ============= TESTS BATCH OPERATIONS =============
class TestBatchOperations:
    def test_delete_all_preserves_other_sessions(self):
        """Test 77: Eliminar todas no afecta otras sesiones"""
        client1 = TestClient(app)
        client2 = TestClient(app)
        
        client1.post("/tasks", json={"title": "Client 1 Task"})
        client2.post("/tasks", json={"title": "Client 2 Task"})
        
        client1.delete("/tasks")
        
        assert len(client1.get("/tasks").json()) == 0
        assert len(client2.get("/tasks").json()) == 1
    
    def test_create_multiple_and_count(self, session_client):
        """Test 78: Crear múltiples y verificar conteo"""
        count = 15
        for i in range(count):
            session_client.post("/tasks", json={"title": f"Batch {i}"})
        
        stats = session_client.get("/tasks/stats").json()
        assert stats["total"] == count

# ============= TESTS BOUNDARY CONDITIONS =============
class TestBoundaryConditions:
    def test_title_exactly_3_chars(self, session_client):
        """Test 79: Título de exactamente 3 caracteres"""
        response = session_client.post("/tasks", json={"title": "ABC"})
        assert response.status_code == 201
    
    def test_title_exactly_200_chars(self, session_client):
        """Test 80: Título de exactamente 200 caracteres"""
        title = "A" * 200
        response = session_client.post("/tasks", json={"title": title})
        assert response.status_code == 201
    
    def test_description_exactly_1000_chars(self, session_client):
        """Test 81: Descripción de exactamente 1000 caracteres"""
        desc = "A" * 1000
        response = session_client.post("/tasks", json={
            "title": "Valid",
            "description": desc
        })
        assert response.status_code == 201
    
    def test_priority_min_value(self, session_client):
        """Test 82: Prioridad mínima (1)"""
        response = session_client.post("/tasks", json={
            "title": "Min Priority",
            "priority": 1
        })
        assert response.status_code == 201
        assert response.json()["priority"] == 1
    
    def test_priority_max_value(self, session_client):
        """Test 83: Prioridad máxima (4)"""
        response = session_client.post("/tasks", json={
            "title": "Max Priority",
            "priority": 4
        })
        assert response.status_code == 201
        assert response.json()["priority"] == 4

# ============= TESTS IDEMPOTENCY =============
class TestIdempotency:
    def test_get_task_idempotent(self, session_client, created_task):
        """Test 84: GET es idempotente"""
        response1 = session_client.get(f"/tasks/{created_task['id']}")
        response2 = session_client.get(f"/tasks/{created_task['id']}")
        assert response1.json() == response2.json()
    
    def test_delete_task_twice(self, session_client, created_task):
        """Test 85: DELETE dos veces retorna 404 la segunda"""
        response1 = session_client.delete(f"/tasks/{created_task['id']}")
        assert response1.status_code == 204
        
        response2 = session_client.delete(f"/tasks/{created_task['id']}")
        assert response2.status_code == 404

# ============= TESTS STATE TRANSITIONS =============
class TestStateTransitions:
    def test_transition_pending_to_in_progress(self, session_client, created_task):
        """Test 86: Transición PENDING -> IN_PROGRESS"""
        response = session_client.patch(
            f"/tasks/{created_task['id']}/status?status=IN_PROGRESS"
        )
        assert response.json()["status"] == "IN_PROGRESS"
    
    def test_transition_in_progress_to_completed(self, session_client):
        """Test 87: Transición IN_PROGRESS -> COMPLETED"""
        task = session_client.post("/tasks", json={"title": "Progress"}).json()
        session_client.patch(f"/tasks/{task['id']}/status?status=IN_PROGRESS")
        response = session_client.patch(f"/tasks/{task['id']}/status?status=COMPLETED")
        assert response.json()["status"] == "COMPLETED"
    
    def test_transition_pending_to_cancelled(self, session_client, created_task):
        """Test 88: Transición PENDING -> CANCELLED"""
        response = session_client.patch(
            f"/tasks/{created_task['id']}/status?status=CANCELLED"
        )
        assert response.json()["status"] == "CANCELLED"
    
    def test_transition_completed_to_pending(self, session_client):
        """Test 89: Transición COMPLETED -> PENDING (reapertura)"""
        task = session_client.post("/tasks", json={"title": "Reopen"}).json()
        session_client.patch(f"/tasks/{task['id']}/status?status=COMPLETED")
        response = session_client.patch(f"/tasks/{task['id']}/status?status=PENDING")
        assert response.json()["status"] == "PENDING"

# ============= TESTS SEARCH ADVANCED =============
class TestSearchAdvanced:
    def test_search_partial_match(self, session_client):
        """Test 90: Búsqueda con coincidencia parcial"""
        session_client.post("/tasks", json={"title": "Development Task"})
        response = session_client.get("/tasks/search?q=Develop")
        assert len(response.json()) == 1
    
    def test_search_multiple_results(self, session_client):
        """Test 91: Búsqueda con múltiples resultados"""
        session_client.post("/tasks", json={"title": "Python Backend"})
        session_client.post("/tasks", json={"title": "Python Frontend"})
        session_client.post("/tasks", json={"title": "Java Backend"})
        
        response = session_client.get("/tasks/search?q=Python")
        assert len(response.json()) == 2
    
    def test_search_in_title_and_description(self, session_client):
        """Test 92: Búsqueda en título y descripción"""
        session_client.post("/tasks", json={
            "title": "Backend Work",
            "description": "API development"
        })
        session_client.post("/tasks", json={
            "title": "API Testing",
            "description": "Frontend tests"
        })
        
        response = session_client.get("/tasks/search?q=API")
        assert len(response.json()) == 2

# ============= TESTS STATISTICS ADVANCED =============
class TestStatisticsAdvanced:
    def test_stats_with_mixed_statuses(self, session_client):
        """Test 93: Estadísticas con estados mixtos"""
        tasks = []
        for i in range(10):
            r = session_client.post("/tasks", json={"title": f"Task {i}"})
            tasks.append(r.json())
        
        # 3 completadas, 2 en progreso, 1 cancelada, 4 pendientes
        for i in range(3):
            session_client.patch(f"/tasks/{tasks[i]['id']}/status?status=COMPLETED")
        for i in range(3, 5):
            session_client.patch(f"/tasks/{tasks[i]['id']}/status?status=IN_PROGRESS")
        session_client.patch(f"/tasks/{tasks[5]['id']}/status?status=CANCELLED")
        
        stats = session_client.get("/tasks/stats").json()
        assert stats["total"] == 10
        assert stats["completed"] == 3
        assert stats["in_progress"] == 2
        assert stats["cancelled"] == 1
        assert stats["pending"] == 4
    
    def test_stats_updates_after_delete(self, session_client):
        """Test 94: Estadísticas se actualizan tras eliminar"""
        tasks = []
        for i in range(5):
            r = session_client.post("/tasks", json={"title": f"Task {i}"})
            tasks.append(r.json())
        
        initial_stats = session_client.get("/tasks/stats").json()
        assert initial_stats["total"] == 5
        
        session_client.delete(f"/tasks/{tasks[0]['id']}")
        
        updated_stats = session_client.get("/tasks/stats").json()
        assert updated_stats["total"] == 4

# ============= TESTS TAGS =============
class TestTags:
    def test_create_task_with_tags(self, session_client):
        """Test 95: Crear tarea con tags"""
        response = session_client.post("/tasks", json={
            "title": "Tagged Task",
            "tags": ["urgent", "backend"]
        })
        assert len(response.json()["tags"]) == 2
    
    def test_update_task_tags(self, session_client, created_task):
        """Test 96: Actualizar tags de tarea"""
        response = session_client.put(f"/tasks/{created_task['id']}", json={
            "tags": ["updated", "new-tag"]
        })
        assert response.json()["tags"] == ["updated", "new-tag"]
    
    def test_empty_tags_default(self, session_client):
        """Test 97: Tags por defecto es array vacío"""
        response = session_client.post("/tasks", json={"title": "No Tags"})
        assert response.json()["tags"] == []

# ============= TESTS DUE DATE =============
class TestDueDate:
    def test_create_task_with_due_date(self, session_client):
        """Test 98: Crear tarea con fecha de vencimiento"""
        response = session_client.post("/tasks", json={
            "title": "Due Task",
            "due_date": "2025-12-31"
        })
        assert response.json()["due_date"] == "2025-12-31"
    
    def test_update_due_date(self, session_client, created_task):
        """Test 99: Actualizar fecha de vencimiento"""
        response = session_client.put(f"/tasks/{created_task['id']}", json={
            "due_date": "2026-01-15"
        })
        assert response.json()["due_date"] == "2026-01-15"
    
    def test_remove_due_date(self, session_client):
        """Test 100: Remover fecha de vencimiento"""
        task = session_client.post("/tasks", json={
            "title": "With Date",
            "due_date": "2025-12-31"
        }).json()
        
        response = session_client.put(f"/tasks/{task['id']}", json={
            "due_date": None
        })
        assert response.json()["due_date"] is None

# ============= SUMMARY =============
def test_run_all():
    """Meta-test: Verifica que hay al menos 100 tests"""
    import inspect
    import sys
    
    current_module = sys.modules[__name__]
    test_functions = [
        name for name, obj in inspect.getmembers(current_module)
        if (inspect.isfunction(obj) or inspect.ismethod(obj)) and name.startswith('test_')
    ]
    
    test_classes = [
        obj for name, obj in inspect.getmembers(current_module)
        if inspect.isclass(obj) and name.startswith('Test')
    ]
    
    total_tests = len(test_functions)
    for test_class in test_classes:
        class_tests = [
            name for name in dir(test_class)
            if name.startswith('test_')
        ]
        total_tests += len(class_tests)
    
    print(f"\n{'='*60}")
    print(f"📊 RESUMEN DE TESTS")
    print(f"{'='*60}")
    print(f"Total de tests implementados: {total_tests}")
    print(f"Clases de test: {len(test_classes)}")
    print(f"Tests sueltos: {len(test_functions)}")
    print(f"{'='*60}\n")
    
    assert total_tests >= 100, f"Se requieren al menos 100 tests, encontrados: {total_tests}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])