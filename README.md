# 📌 **SantiagoList API (FastAPI + SOLID + Repository Pattern)**

# Task Management API (FastAPI)

API RESTful moderna, robusta y mantenible, diseñada bajo principios **SOLID**, **Repository Pattern**, **Service Layer** y gestión de sesiones mediante **cookies seguras**, sin base de datos, completamente in-memory.

---

## 🚀 **Descripción General**

Este proyecto implementa un sistema completo para la gestión de tareas utilizando **FastAPI**, aplicando buenas prácticas de arquitectura, desacoplamiento y organización del código.
La API es liviana, rápida y está optimizada para funcionar sin una base de datos tradicional. En su lugar, utiliza:

✔ **Almacenamiento de datos en memoria por sesión**
✔ **Identificación del cliente mediante cookies**
✔ **Thread-Safety gracias a `Lock()`**
✔ **Patrones de diseño para separar lógica de negocios y acceso a datos**

---

## 🧩 **Características Principales**

* CRUD completo de tareas (crear, listar, actualizar, eliminar).
* Endpoint de estadísticas globales.
* Búsqueda inteligente por texto.
* Manejo de sesiones con cookies automáticas (`session_id`).
* Persistencia temporal por usuario sin necesidad de autenticación.
* Arquitectura limpia con:

  * `Repository Pattern`
  * `Service Layer`
  * Modelos Pydantic con validaciones avanzadas
* Manejo global de excepciones.
* CORS configurado para despliegue en Vercel, local y entornos híbridos.
* Logging integrado.

---

## 🏛️ **Arquitectura del Proyecto**

```txt
┌────────────────────────┐
│       FastAPI          │
│   (Controllers/API)    │
└──────────┬─────────────┘
           │
           ▼
┌────────────────────────┐
│     Service Layer      │
│   (Business Logic)     │
└──────────┬─────────────┘
           │
           ▼
┌────────────────────────┐
│   Repository Pattern   │
│ (InMemory Repository)  │
└────────────────────────┘
```

---

## 🧱 **Patrones Implementados**

### **1. Repository Pattern**

Permite desacoplar la API del almacenamiento.

```python
class IRepository(ABC):
    @abstractmethod
    def find_all(self): ...
    @abstractmethod
    def create(self): ...
```

### **2. Service Layer**

Toda la lógica de negocio se maneja en una sola capa:

* Validaciones
* Transformaciones
* Reglas de negocio

### **3. Dependency Injection**

FastAPI facilita la inyección de dependencias para:

* Repositorio
* Servicio de tareas
* Manejo de sesión

---

## 🧪 **Modelos de Datos**

### **Task**

```json
{
  "id": "uuid",
  "title": "string",
  "description": "string",
  "priority": 1,
  "status": "PENDING",
  "tags": ["string"],
  "due_date": "string",
  "created_at": "ISODate",
  "updated_at": "ISODate"
}
```

---

## 🍪 **Manejo de Sesiones con Cookies**

Cada cliente obtiene una cookie automática:

```
session_id=uuid; httponly; secure; samesite=none;
```

Esto permite:

* Separar las tareas por usuario
* No usar autenticación
* Evitar bases de datos

El sistema almacena datos así:

```python
self._storage = {
    "id_de_sesion": [ {task}, {task} ]
}
```

---

## ⚙️ **Instalación y Ejecución**

### **1. Crear entorno virtual**

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

### **2. Instalar dependencias**

```bash
pip install fastapi uvicorn
```

### **3. Ejecutar servidor**

```bash
uvicorn main:app --reload
```

API disponible en:
👉 [http://127.0.0.1:8000](http://127.0.0.1:8000)
Documentación automática:
👉 [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
👉 [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 📡 **Endpoints Principales**

### ✔ Health Check

```
GET /health
```

### ✔ Listar tareas

```
GET /tasks
```

### ✔ Crear tarea

```
POST /tasks
```

### ✔ Buscar tareas

```
GET /tasks/search?q=texto
```

### ✔ Estadísticas

```
GET /tasks/stats
```

### ✔ Actualizar tarea

```
PUT /tasks/{id}
```

### ✔ Cambiar estado

```
PATCH /tasks/{id}/status
```

### ✔ Eliminar tarea

```
DELETE /tasks/{id}
```

### ✔ Eliminar todas las tareas

```
DELETE /tasks
```

---

## 📂 **Estructura del Código**

```txt
main.py
│
├── CORS middleware
├── Enums: TaskStatus, Priority
├── Modelos con Pydantic
├── Repository Pattern (InMemory)
├── Service Layer
├── Session Manager
├── Endpoints REST
└── Manejo global de errores
```

---

## 🧠 **Principios SOLID aplicados**

* **S – Single Responsibility:** cada clase cumple un propósito aislado.
* **O – Open/Closed:** el repositorio se puede reemplazar por uno SQL sin tocar la lógica.
* **L – Liskov Substitution:** el repositorio base es 100% intercambiable.
* **I – Interface Segregation:** se usa una interfaz pequeña y específica.
* **D – Dependency Inversion:** la API depende de una abstracción (`IRepository`).

---

## 🪵 **Logging Integrado**

Cada creación, actualización o eliminación de tarea genera un log:

```
INFO: Task created: <uuid>
INFO: Task updated: <uuid>
INFO: Task deleted: <uuid>
```

---

## ❗ Manejo Global de Errores

La API captura:

* Errores HTTP con JSON personalizado
* Errores inesperados (`500`)

Ejemplo:

```json
{
  "detail": "Task not found",
  "status_code": 404,
  "timestamp": "2025-01-01T12:00:00Z"
}
```

---

## 🚀 **Despliegue en Producción**

Compatible con:

* Render
* Railway
* Docker
* Vercel (a través de un backend externo)
* Fly.io

Ejemplo de comando para producción:

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

---
