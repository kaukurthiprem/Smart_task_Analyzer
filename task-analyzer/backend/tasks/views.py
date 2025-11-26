from typing import List
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .serializers import TaskInputSerializer, TaskOutputSerializer
from .scoring import score_tasks

def _add_cors_headers(resp: Response) -> Response:
    resp['Access-Control-Allow-Origin'] = '*'
    resp['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    resp['Access-Control-Allow-Headers'] = 'Content-Type'
    return resp

@api_view(['POST', 'OPTIONS'])
def analyze_tasks(request):
    if request.method == 'OPTIONS':
        return _add_cors_headers(Response(status=status.HTTP_200_OK))

    payload = request.data or {}
    tasks_data = payload.get('tasks', [])
    strategy = payload.get('strategy', 'smart_balance')

    serializer = TaskInputSerializer(data=tasks_data, many=True)
    if not serializer.is_valid():
        resp = Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        return _add_cors_headers(resp)

    validated_tasks: List[dict] = serializer.validated_data

    scored, warnings = score_tasks(validated_tasks, strategy=strategy)

    output_serializer = TaskOutputSerializer(
        [s.data for s in scored],
        many=True
    )
    resp = Response(
        {
            'strategy': strategy,
            'warnings': warnings,
            'tasks': output_serializer.data
        }
    )
    return _add_cors_headers(resp)

@api_view(['GET', 'OPTIONS'])
def suggest_tasks(request):
    if request.method == 'OPTIONS':
        return _add_cors_headers(Response(status=status.HTTP_200_OK))

    # Expect tasks JSON string in query params for a stateless API
    import json
    raw_tasks = request.query_params.get('tasks', '[]')
    strategy = request.query_params.get('strategy', 'smart_balance')

    try:
        tasks_list = json.loads(raw_tasks)
    except json.JSONDecodeError:
        resp = Response(
            {'error': 'Invalid tasks payload, expected JSON array in "tasks" query parameter.'},
            status=status.HTTP_400_BAD_REQUEST
        )
        return _add_cors_headers(resp)

    serializer = TaskInputSerializer(data=tasks_list, many=True)
    if not serializer.is_valid():
        resp = Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        return _add_cors_headers(resp)

    validated_tasks: List[dict] = serializer.validated_data

    scored, warnings = score_tasks(validated_tasks, strategy=strategy)
    top3 = scored[:3]
    output_serializer = TaskOutputSerializer(
        [s.data for s in top3],
        many=True
    )
    resp = Response(
        {
            'strategy': strategy,
            'warnings': warnings,
            'suggested_tasks': output_serializer.data
        }
    )
    return _add_cors_headers(resp)