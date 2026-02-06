from sqlalchemy import Uuid

from app.models import (
    DependencyEdgeModel,
    LeaseModel,
    MilestoneModel,
    PhaseModel,
    PlanChangeSetModel,
    PlanVersionModel,
    ProjectModel,
    TaskExecutionSnapshotModel,
    TaskModel,
    TaskReservationModel,
)


def test_id_and_fk_columns_use_uuid_type_for_postgres_compat():
    uuid_columns = [
        ProjectModel.__table__.c.id,
        PhaseModel.__table__.c.id,
        PhaseModel.__table__.c.project_id,
        MilestoneModel.__table__.c.id,
        MilestoneModel.__table__.c.project_id,
        MilestoneModel.__table__.c.phase_id,
        TaskModel.__table__.c.id,
        TaskModel.__table__.c.project_id,
        TaskModel.__table__.c.phase_id,
        TaskModel.__table__.c.milestone_id,
        DependencyEdgeModel.__table__.c.id,
        DependencyEdgeModel.__table__.c.project_id,
        DependencyEdgeModel.__table__.c.from_task_id,
        DependencyEdgeModel.__table__.c.to_task_id,
        LeaseModel.__table__.c.id,
        LeaseModel.__table__.c.project_id,
        LeaseModel.__table__.c.task_id,
        TaskReservationModel.__table__.c.id,
        TaskReservationModel.__table__.c.project_id,
        TaskReservationModel.__table__.c.task_id,
        PlanVersionModel.__table__.c.id,
        PlanVersionModel.__table__.c.project_id,
        PlanVersionModel.__table__.c.change_set_id,
        PlanChangeSetModel.__table__.c.id,
        PlanChangeSetModel.__table__.c.project_id,
        TaskExecutionSnapshotModel.__table__.c.id,
        TaskExecutionSnapshotModel.__table__.c.project_id,
        TaskExecutionSnapshotModel.__table__.c.task_id,
        TaskExecutionSnapshotModel.__table__.c.lease_id,
    ]

    assert all(isinstance(column.type, Uuid) for column in uuid_columns)
