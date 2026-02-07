from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

from app.models import ArtifactModel, GateDecisionModel, TaskModel


def test_task_path_and_capability_columns_map_to_postgres_text_arrays():
    pg = postgresql.dialect()
    array_columns = [
        TaskModel.__table__.c.capability_tags,
        TaskModel.__table__.c.expected_touches,
        TaskModel.__table__.c.exclusive_paths,
        TaskModel.__table__.c.shared_paths,
    ]
    assert all(isinstance(column.type.dialect_impl(pg), ARRAY) for column in array_columns)


def test_json_list_columns_map_to_postgres_jsonb():
    pg = postgresql.dialect()
    jsonb_columns = [
        ArtifactModel.__table__.c.touched_files,
        GateDecisionModel.__table__.c.evidence_refs,
    ]
    assert all(isinstance(column.type.dialect_impl(pg), JSONB) for column in jsonb_columns)
