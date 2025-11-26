from django.db import models

class Task(models.Model):
    title = models.CharField(max_length=255)
    due_date = models.DateField(null=True, blank=True)
    estimated_hours = models.FloatField(null=True, blank=True)
    importance = models.IntegerField(default=5)
    # Self-referential many-to-many for dependencies
    dependencies = models.ManyToManyField('self', symmetrical=False, blank=True, related_name='blocked_tasks')

    def __str__(self) -> str:
        return self.title