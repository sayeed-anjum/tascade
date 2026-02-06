from app.models import (
    DependencyEdgeModel,
    LeaseModel,
    PlanChangeSetModel,
    ProjectModel,
    TaskModel,
    TaskReservationModel,
)


def test_model_enums_use_lowercase_value_variants():
    assert ProjectModel.__table__.c.status.type.enums == ["active", "paused", "archived"]
    assert TaskModel.__table__.c.state.type.enums == [
        "backlog",
        "ready",
        "reserved",
        "claimed",
        "in_progress",
        "implemented",
        "integrated",
        "conflict",
        "blocked",
        "abandoned",
        "cancelled",
    ]
    assert TaskModel.__table__.c.task_class.type.enums == [
        "architecture",
        "db_schema",
        "security",
        "cross_cutting",
        "frontend",
        "backend",
        "crud",
        "other",
    ]
    assert DependencyEdgeModel.__table__.c.unlock_on.type.enums == ["implemented", "integrated"]
    assert LeaseModel.__table__.c.status.type.enums == ["active", "expired", "released", "consumed"]
    assert TaskReservationModel.__table__.c.status.type.enums == [
        "active",
        "expired",
        "released",
        "consumed",
    ]
    assert PlanChangeSetModel.__table__.c.status.type.enums == [
        "draft",
        "validated",
        "applied",
        "rejected",
    ]
