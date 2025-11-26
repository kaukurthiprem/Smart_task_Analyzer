from django.test import SimpleTestCase
from datetime import date, timedelta

from .scoring import score_tasks

class ScoringTests(SimpleTestCase):
    def test_importance_affects_score(self):
        today = date.today().isoformat()
        tasks = [
            {'id': '1', 'title': 'Low importance', 'due_date': today, 'estimated_hours': 2, 'importance': 2, 'dependencies': []},
            {'id': '2', 'title': 'High importance', 'due_date': today, 'estimated_hours': 2, 'importance': 9, 'dependencies': []},
        ]
        scored, _ = score_tasks(tasks, strategy='high_impact')
        self.assertEqual(scored[0].data['id'], '2')

    def test_urgency_affects_score(self):
        today = date.today()
        soon = (today + timedelta(days=1)).isoformat()
        later = (today + timedelta(days=20)).isoformat()
        tasks = [
            {'id': '1', 'title': 'Soon', 'due_date': soon, 'estimated_hours': 3, 'importance': 5, 'dependencies': []},
            {'id': '2', 'title': 'Later', 'due_date': later, 'estimated_hours': 3, 'importance': 5, 'dependencies': []},
        ]
        scored, _ = score_tasks(tasks, strategy='deadline_driven')
        self.assertEqual(scored[0].data['id'], '1')

    def test_dependencies_raise_priority(self):
        today = date.today().isoformat()
        tasks = [
            {'id': 'A', 'title': 'Foundation', 'due_date': today, 'estimated_hours': 4, 'importance': 6, 'dependencies': []},
            {'id': 'B', 'title': 'Dependent 1', 'due_date': today, 'estimated_hours': 4, 'importance': 6, 'dependencies': ['A']},
            {'id': 'C', 'title': 'Dependent 2', 'due_date': today, 'estimated_hours': 4, 'importance': 6, 'dependencies': ['A']},
        ]
        scored, _ = score_tasks(tasks, strategy='smart_balance')
        # Foundation task A should be scored higher because it unblocks B and C
        top_ids = [t.data['id'] for t in scored]
        self.assertEqual(top_ids[0], 'A')

    def test_circular_dependencies_penalized(self):
        today = date.today().isoformat()
        tasks = [
            {'id': '1', 'title': 'Task 1', 'due_date': today, 'estimated_hours': 2, 'importance': 8, 'dependencies': ['2']},
            {'id': '2', 'title': 'Task 2', 'due_date': today, 'estimated_hours': 2, 'importance': 8, 'dependencies': ['1']},
        ]
        scored, warnings = score_tasks(tasks, strategy='smart_balance')
        self.assertTrue(any('circular' in w.lower() for w in warnings))
        # Both tasks should still be scored, but with penalty applied
        for s in scored:
            self.assertLess(s.score, 100.0)