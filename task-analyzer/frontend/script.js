const API_BASE = "http://localhost:8000/api";

let tasks = [];
let nextId = 1;

const taskForm = document.getElementById("task-form");
const strategySelect = document.getElementById("strategy-select");
const bulkTextarea = document.getElementById("bulk-json");
const loadBulkBtn = document.getElementById("load-bulk");
const analyzeBtn = document.getElementById("analyze-tasks");
const suggestBtn = document.getElementById("suggest-tasks");
const taskListEl = document.getElementById("task-list");
const suggestedListEl = document.getElementById("suggested-list");
const statusEl = document.getElementById("status");

function setStatus(message, isError = false) {
    statusEl.textContent = message || "";
    statusEl.style.color = isError ? "#b91c1c" : "#374151";
}

function renderTasks(targetEl, data) {
    targetEl.innerHTML = "";
    if (!data || data.length === 0) {
        targetEl.innerHTML = "<p>No tasks to display.</p>";
        return;
    }

    data.forEach((task) => {
        const card = document.createElement("div");
        card.className = "task-card";

        const header = document.createElement("div");
        header.className = "task-header";

        const title = document.createElement("span");
        title.className = "task-title";
        title.textContent = `${task.id || "-"} • ${task.title}`;

        const badge = document.createElement("span");
        let label = (task.priority_label || "").toLowerCase();
        badge.className = "badge " + (label === "high" ? "high" : label === "medium" ? "medium" : "low");
        badge.textContent = `${task.priority_label || "N/A"} (${task.score ?? "?"})`;

        header.appendChild(title);
        header.appendChild(badge);

        const meta = document.createElement("div");
        meta.className = "meta";
        meta.textContent = [
            task.due_date ? `Due: ${task.due_date}` : "No due date",
            task.estimated_hours != null ? `Est: ${task.estimated_hours}h` : "Est: N/A",
            `Importance: ${task.importance}`,
            `Depends on: ${(task.dependencies || []).join(", ") || "None"}`
        ].join(" • ");

        const explanation = document.createElement("div");
        explanation.className = "explanation";
        explanation.textContent = task.explanation || "";

        card.appendChild(header);
        card.appendChild(meta);
        card.appendChild(explanation);

        targetEl.appendChild(card);
    });
}

function renderLocalTasks() {
    renderTasks(taskListEl, tasks);
}

taskForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const title = document.getElementById("title").value.trim();
    const dueDate = document.getElementById("due_date").value || null;
    const estimatedHoursStr = document.getElementById("estimated_hours").value;
    const importanceStr = document.getElementById("importance").value;
    const depsStr = document.getElementById("dependencies").value.trim();

    if (!title) {
        setStatus("Title is required.", true);
        return;
    }

    const importance = parseInt(importanceStr, 10);
    if (Number.isNaN(importance) || importance < 1 || importance > 10) {
        setStatus("Importance must be between 1 and 10.", true);
        return;
    }

    let estimated_hours = null;
    if (estimatedHoursStr !== "") {
        const val = parseFloat(estimatedHoursStr);
        if (Number.isNaN(val) || val < 0) {
            setStatus("Estimated hours must be a positive number.", true);
            return;
        }
        estimated_hours = val;
    }

    let dependencies = [];
    if (depsStr) {
        dependencies = depsStr.split(",").map((s) => s.trim()).filter(Boolean);
    }

    const task = {
        id: String(nextId++),
        title,
        due_date: dueDate || null,
        estimated_hours,
        importance,
        dependencies,
    };

    tasks.push(task);
    setStatus("Task added.");
    taskForm.reset();
    renderLocalTasks();
});

loadBulkBtn.addEventListener("click", () => {
    const raw = bulkTextarea.value.trim();
    if (!raw) {
        setStatus("Paste a JSON array first.", true);
        return;
    }
    try {
        const parsed = JSON.parse(raw);
        if (!Array.isArray(parsed)) {
            throw new Error("JSON must be an array of tasks");
        }
        tasks = parsed.map((t) => {
            const cloned = { ...t };
            if (!cloned.id) {
                cloned.id = String(nextId++);
            }
            if (!Array.isArray(cloned.dependencies)) {
                cloned.dependencies = [];
            }
            return cloned;
        });
        // Adjust nextId so we don't clash
        const numericIds = tasks
            .map((t) => parseInt(t.id, 10))
            .filter((n) => !Number.isNaN(n));
        if (numericIds.length > 0) {
            nextId = Math.max(...numericIds) + 1;
        }
        setStatus("Loaded tasks from JSON.");
        renderLocalTasks();
    } catch (err) {
        console.error(err);
        setStatus("Invalid JSON: " + err.message, true);
    }
});

analyzeBtn.addEventListener("click", async () => {
    if (tasks.length === 0) {
        setStatus("Add at least one task before analyzing.", true);
        return;
    }
    setStatus("Analyzing tasks...");
    suggestedListEl.innerHTML = "";
    try {
        const res = await fetch(`${API_BASE}/tasks/analyze/`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                strategy: strategySelect.value,
                tasks,
            }),
        });

        if (!res.ok) {
            const errBody = await res.json().catch(() => ({}));
            throw new Error(errBody.error || "API error");
        }

        const data = await res.json();
        if (Array.isArray(data.tasks)) {
            tasks = data.tasks;
            setStatus(`Analyzed using strategy: ${data.strategy}.`);
            renderTasks(taskListEl, tasks);
        } else {
            setStatus("Unexpected API response.", true);
        }
    } catch (err) {
        console.error(err);
        setStatus("Failed to analyze tasks: " + err.message, true);
    }
});

suggestBtn.addEventListener("click", async () => {
    if (tasks.length === 0) {
        setStatus("Add at least one task before requesting suggestions.", true);
        return;
    }
    setStatus("Fetching suggestions...");
    try {
        const params = new URLSearchParams();
        params.set("strategy", strategySelect.value);
        params.set("tasks", JSON.stringify(tasks));

        const res = await fetch(`${API_BASE}/tasks/suggest/?${params.toString()}`);
        if (!res.ok) {
            const errBody = await res.json().catch(() => ({}));
            throw new Error(errBody.error || "API error");
        }
        const data = await res.json();
        if (Array.isArray(data.suggested_tasks)) {
            setStatus(`Top ${data.suggested_tasks.length} tasks suggested.`);
            renderTasks(suggestedListEl, data.suggested_tasks);
        } else {
            setStatus("Unexpected API response.", true);
        }
    } catch (err) {
        console.error(err);
        setStatus("Failed to fetch suggestions: " + err.message, true);
    }
});

// Initial render
renderLocalTasks();