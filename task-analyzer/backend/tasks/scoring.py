from __future__ import annotations
from dataclasses import dataclass
from datetime import date, datetime
from typing import List, Dict, Tuple, Set

@dataclass
class ScoredTask:
    data: Dict
    score: float
    priority_label: str
    explanation: str

def _parse_due_date(val) -> date | None:
    if not val:
        return None
    if isinstance(val, date):
        return val
    try:
        return datetime.strptime(str(val), "%Y-%m-%d").date()
    except Exception:
        return None

def _urgency_score(due: date | None, today: date | None = None) -> float:
    if today is None:
        today = date.today()
    if due is None:
        # Neutral urgency
        return 0.5
    days_diff = (due - today).days
    if days_diff < 0:
        # Already overdue, max urgency
        return 1.0
    # Map 0-30 days to 1.0-0.0 linearly, clamp beyond 30 days
    if days_diff >= 30:
        return 0.0
    return 1.0 - (days_diff / 30.0)

def _importance_score(importance: int | None) -> float:
    if importance is None:
        return 0.5
    importance = max(1, min(10, int(importance)))
    return importance / 10.0

def _effort_score(hours: float | None) -> float:
    if hours is None:
        return 0.5
    try:
        h = float(hours)
    except Exception:
        return 0.5
    if h <= 0:
        return 0.8
    # We consider <=2h tasks as quick wins, >=8h as heavy
    if h <= 2:
        return 1.0
    if h >= 8:
        return 0.1
    # Linearly interpolate between 2h->1.0 and 8h->0.1
    return 1.0 - ((h - 2.0) / 6.0) * 0.9

def detect_circular_dependencies(tasks: List[Dict]) -> Set[str]:
    """Return a set of task IDs that are part of any circular dependency."""
    graph: Dict[str, List[str]] = {}
    for t in tasks:
        tid = str(t.get("id", ""))
        if not tid:
            continue
        deps = [str(d) for d in t.get("dependencies") or []]
        graph[tid] = deps

    visited: Set[str] = set()
    stack: Set[str] = set()
    in_cycle: Set[str] = set()

    def dfs(node: str):
        if node in stack:
            # Found a cycle: mark all current stack as in_cycle
            in_cycle.update(stack)
            return
        if node in visited:
            return
        visited.add(node)
        stack.add(node)
        for neigh in graph.get(node, []):
            dfs(neigh)
        stack.remove(node)

    for node in list(graph.keys()):
        if node not in visited:
            dfs(node)
    return in_cycle

def _dependency_influence(tasks: List[Dict]) -> Dict[str, float]:
    """Return mapping task_id -> dependency factor based on how many tasks depend on it."""
    dependents_count: Dict[str, int] = {}
    for t in tasks:
        tid = str(t.get("id", ""))
        if not tid:
            continue
        dependents_count.setdefault(tid, 0)

    for t in tasks:
        deps = [str(d) for d in (t.get("dependencies") or [])]
        for d in deps:
            if d in dependents_count:
                dependents_count[d] += 1

    if not dependents_count:
        return {}

    max_dependents = max(dependents_count.values()) or 1
    return {tid: cnt / max_dependents for tid, cnt in dependents_count.items()}

def _priority_label(score: float) -> str:
    if score >= 80:
        return "High"
    if score >= 50:
        return "Medium"
    return "Low"

def score_tasks(tasks: List[Dict], strategy: str = "smart_balance") -> Tuple[List[ScoredTask], List[str]]:
    """Score and sort tasks.

    Returns:
        (sorted_scored_tasks, warnings)
    """
    strategy = strategy or "smart_balance"
    strategy = strategy.lower()

    warnings: List[str] = []

    # Detect circular dependencies
    circular_ids = detect_circular_dependencies(tasks)
    if circular_ids:
        warnings.append(
            f"Detected circular dependencies involving task IDs: {', '.join(sorted(circular_ids))}."
        )

    dep_influence = _dependency_influence(tasks)

    today = date.today()
    scored: List[ScoredTask] = []

    for raw in tasks:
        t = dict(raw)  # copy
        title = t.get("title") or "Untitled Task"
        tid = str(t.get("id", "")) or None

        due = _parse_due_date(t.get("due_date"))
        urgency = _urgency_score(due, today)
        importance = _importance_score(t.get("importance"))
        effort = _effort_score(t.get("estimated_hours"))
        dep_factor = dep_influence.get(tid, 0.0 if tid else 0.0)

        # Base weights per strategy
        if strategy == "fastest_wins":
            w_u, w_i, w_e, w_d = 0.25, 0.25, 0.50, 0.00
        elif strategy == "high_impact":
            w_u, w_i, w_e, w_d = 0.20, 0.60, 0.10, 0.10
        elif strategy == "deadline_driven":
            w_u, w_i, w_e, w_d = 0.60, 0.20, 0.10, 0.10
        else:  # smart_balance
            w_u, w_i, w_e, w_d = 0.35, 0.35, 0.15, 0.15

        base_score_0_1 = (
            urgency * w_u +
            importance * w_i +
            effort * w_e +
            dep_factor * w_d
        )

        # Penalty for circular dependency involvement
        penalty = 0.0
        if tid and tid in circular_ids:
            penalty += 0.2  # 20% penalty

        if t.get("due_date") and due is None:
            warnings.append(
                f"Task '{title}' has invalid due_date value '{t.get('due_date')}', treated as no due date."
            )

        if t.get("estimated_hours") is None:
            warnings.append(
                f"Task '{title}' missing estimated_hours, using neutral effort in scoring."
            )

        # Convert to 0-100 and apply penalty
        score = max(0.0, (base_score_0_1 - penalty) * 100.0)

        label = _priority_label(score)

        explanation_parts = []
        if urgency >= 0.8:
            explanation_parts.append("Very urgent (due soon or overdue).")
        elif urgency >= 0.5:
            explanation_parts.append("Moderately urgent.")
        else:
            explanation_parts.append("Not very time-sensitive.")

        if importance >= 0.8:
            explanation_parts.append("High business impact.")
        elif importance <= 0.4:
            explanation_parts.append("Lower importance compared to other tasks.")

        if effort >= 0.8:
            explanation_parts.append("Quick win with low effort.")
        elif effort <= 0.3:
            explanation_parts.append("Larger task that may require more planning.")

        if dep_factor >= 0.6:
            explanation_parts.append("Unblocks several other tasks.")
        elif dep_factor > 0:
            explanation_parts.append("Unblocks at least one other task.")

        if tid and tid in circular_ids:
            explanation_parts.append("Involved in a circular dependency, penalized in score until graph is fixed.")

        explanation = " ".join(explanation_parts) or "Balanced across urgency, importance, effort, and dependencies."

        t["score"] = round(score, 2)
        t["priority_label"] = label
        t["explanation"] = explanation

        scored.append(ScoredTask(data=t, score=score, priority_label=label, explanation=explanation))

    scored.sort(key=lambda st: st.score, reverse=True)
    return scored, warnings