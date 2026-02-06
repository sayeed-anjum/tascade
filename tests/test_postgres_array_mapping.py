from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import ARRAY

from app.models import TaskModel


def test_task_path_and_capability_columns_map_to_postgres_text_arrays():
    pg = postgresql.dialect()
    array_columns = [
        TaskModel.__table__.c.capability_tags,
        TaskModel.__table__.c.expected_touches,
        TaskModel.__table__.c.exclusive_paths,
        TaskModel.__table__.c.shared_paths,
    ]
    assert all(isinstance(column.type.dialect_impl(pg), ARRAY) for column in array_columns)
