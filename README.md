# Smart Task Analyzer – Singularium Internship Assignment

This repository contains a mini-application that scores and prioritizes tasks based on
urgency, importance, effort, and dependencies.

Backend: **Python / Django / Django REST Framework**  
Frontend: **HTML / CSS / JavaScript**

The goal is to help users decide **what to work on first** using different prioritization
strategies.

## 1. Project Structure

```
task-analyzer/
├── backend/
│   ├── manage.py
│   ├── requirements.txt
│   ├── task_analyzer/
│   │   ├── __init__.py
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   └── tasks/
│       ├── __init__.py
│       ├── apps.py
│       ├── models.py
│       ├── serializers.py
│       ├── scoring.py
│       ├── views.py
│       ├── urls.py
│       └── tests.py
├── frontend/
│   ├── index.html
│   ├── styles.css
│   └── script.js
└── README.md
```

## 2. Setup Instructions

### 2.1 Backend (Django API)

1. Create and activate a virtual environment (recommended):

   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Apply migrations and run the server:

   ```bash
   python manage.py migrate
   python manage.py runserver  # defaults to http://127.0.0.1:8000
   ```

The API will be available under: `http://localhost:8000/api/`.

### 2.2 Frontend

A simple option is to serve the `frontend/` directory using a static file server:

```bash
cd frontend
python -m http.server 5500
```

Then open: `http://localhost:5500/index.html` in your browser.

The frontend is configured to call the backend at `http://localhost:8000/api`.

> Note: Basic CORS headers are added in the Django views so the browser can call the API from a different port.

## 3. API Endpoints

### `POST /api/tasks/analyze/`

**Body:**

```json
{
  "strategy": "smart_balance",
  "tasks": [
    {
      "id": "1",
      "title": "Fix login bug",
      "due_date": "2025-11-30",
      "estimated_hours": 3,
      "importance": 8,
      "dependencies": []
    }
  ]
}
```

**Response:**

```json
{
  "strategy": "smart_balance",
  "warnings": [],
  "tasks": [
    {
      "id": "1",
      "title": "Fix login bug",
      "due_date": "2025-11-30",
      "estimated_hours": 3.0,
      "importance": 8,
      "dependencies": [],
      "score": 78.5,
      "priority_label": "High",
      "explanation": "Very urgent (due soon or overdue). High business impact. Quick win with low effort."
    }
  ]
}
```

### `GET /api/tasks/suggest/`

Stateless endpoint that returns the **top 3** tasks for today.

**Query parameters:**

- `strategy`: one of `smart_balance`, `fastest_wins`, `high_impact`, `deadline_driven`
- `tasks`: JSON-encoded array of task objects (same shape as above)

Example URL (shortened):

```
/api/tasks/suggest/?strategy=smart_balance&tasks=[...json...]
```

**Response:**

```json
{
  "strategy": "smart_balance",
  "warnings": [],
  "suggested_tasks": [
    { "id": "1", "title": "Fix login bug", "...": "..." },
    { "id": "3", "title": "Prepare release notes", "...": "..." },
    { "id": "2", "title": "Refactor dashboard", "...": "..." }
  ]
}
```

## 4. Priority Scoring Algorithm (Core Logic)

The core logic is implemented in `backend/tasks/scoring.py`.

Each task is scored on a 0–100 scale and labeled as:

- **High** priority ≥ 80
- **Medium** priority 50–79
- **Low** priority < 50

Factors considered:

1. **Urgency**  
   - Based on days until due date.
   - Overdue tasks get maximum urgency.
   - Tasks within the next 30 days are mapped linearly from high to low urgency.
   - Tasks without a due date get neutral urgency (0.5).

2. **Importance**  
   - User-provided scale 1–10, normalized to 0–1.
   - Higher importance strongly boosts the score in most strategies.

3. **Effort (Estimated Hours)**  
   - Models “quick wins” vs “heavy tasks”.
   - ≤ 2h → considered quick wins (score ~1.0).
   - ≥ 8h → heavy tasks (score ~0.1).
   - Smooth linear interpolation in-between.

4. **Dependencies (Blocking Power)**  
   - We build a small dependency graph (using task IDs).
   - For each task we count how many other tasks depend on it.
   - The count is normalized (0–1) so tasks that unblock many others get a higher factor.

5. **Circular Dependency Detection**  
   - We perform a DFS over the dependency graph.
   - Any task involved in a cycle is:
     - Reported in the `warnings` list.
     - Penalized in the final score (e.g. −20% of the normalized score).
   - This encourages fixing the dependency graph before relying on the ranking.

### 4.1 Strategies

The algorithm supports multiple strategies via different weights:

- **Smart Balance (default)**
  - Balances urgency and importance, but still considers effort and dependencies.
  - Weights (Urgency / Importance / Effort / Dependency) roughly: `0.35 / 0.35 / 0.15 / 0.15`.

- **Fastest Wins**
  - Optimizes for momentum and quick delivery.
  - Emphasizes low-effort tasks while still considering importance and urgency.
  - Weights: `0.25 / 0.25 / 0.50 / 0.00`.

- **High Impact**
  - Focuses on business impact first.
  - Importance dominates the score, with urgency and dependency as secondary.
  - Weights: `0.20 / 0.60 / 0.10 / 0.10`.

- **Deadline Driven**
  - Ideal for crunch-time scenarios.
  - Urgency dominates, with some importance and dependency influence.
  - Weights: `0.60 / 0.20 / 0.10 / 0.10`.

Final score formula (conceptually):

```text
score_0_to_1 = urgency * w_u
             + importance * w_i
             + effort_quickwin * w_e
             + dep_influence * w_d

score_0_to_100 = max(0, (score_0_to_1 - penalty) * 100)
```

Where `penalty` is applied for circular dependencies.

The explanation string for each task is generated based on the dominant factors:
urgent due dates, high importance, low effort, and strong dependency influence.

## 5. Design Decisions & Trade-offs

- **Stateless API**:  
  To keep the API simple and avoid database persistence for this assignment,
  both endpoints work purely off the payload provided by the client. This makes
  it easy to test and reason about.

- **ID-based Dependencies**:  
  Dependencies are expressed as lists of task IDs (strings). This keeps the
  model close to the assignment’s JSON structure and works well with the
  in-memory scoring algorithm.

- **CORS Handling**:  
  Since the frontend and backend typically run on different ports in local
  development, basic `Access-Control-Allow-Origin: *` headers are added
  directly in the Django views instead of pulling in an extra dependency.

- **Graceful Handling of Missing / Invalid Data**:  
  - Missing `estimated_hours` → neutral effort.
  - Missing `due_date` → neutral urgency.
  - Invalid `due_date` strings are treated as “no due date” and surfaced as warnings.

- **No Over-Engineering**:  
  The scoring logic is intentionally implemented as simple pure functions
  in `scoring.py` for readability and testability.

## 6. Time Breakdown (Approximate)

- Algorithm design and implementation: ~1.5 hours  
- Django API (serializers, views, urls, CORS): ~1 hour  
- Frontend (UI, event handling, API integration): ~1 hour  
- Unit tests and documentation: ~30–45 minutes  

## 7. Bonus / Future Improvements

Potential extensions if more time were available:

- **Dependency Graph Visualization** using a simple JS library or canvas to
  render a directed graph and highlight cycles.
- **Date Intelligence** that accounts for weekends/holidays when computing urgency.
- **Eisenhower Matrix View** plotting tasks in a 2×2 grid (Urgent vs Important).
- **Learning System** where users mark suggestions as helpful/not helpful and
  the system adjusts weights over time.
- **Persistent Storage**: store tasks in the Django database, track completion,
  and maintain user-specific preferences for strategies and weights.

## 8. Running Tests

From the `backend` directory:

```bash
python manage.py test tasks
```

This executes the unit tests for the scoring algorithm located in `tasks/tests.py`.