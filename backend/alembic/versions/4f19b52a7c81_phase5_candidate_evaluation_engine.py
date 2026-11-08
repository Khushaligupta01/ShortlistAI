"""phase5_candidate_evaluation_engine

Revision ID: 4f19b52a7c81
Revises: 3e089431a456
Create Date: 2026-11-08 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from app.db.base import GUID

# revision identifiers, used by Alembic.
revision = '4f19b52a7c81'
down_revision = '3e089431a456'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create evaluation_runs table
    op.create_table(
        'evaluation_runs',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('requisition_id', GUID(), nullable=False),
        sa.Column('organization_id', GUID(), nullable=False),
        sa.Column('initiated_by', GUID(), nullable=False),
        sa.Column('total_candidates', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('completed_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='PENDING'),
        sa.Column('error_summary', sa.JSON(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['requisition_id'], ['requisitions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['initiated_by'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_evaluation_runs_org_id', 'evaluation_runs', ['organization_id'], unique=False)
    op.create_index('ix_evaluation_runs_req_id', 'evaluation_runs', ['requisition_id'], unique=False)
    op.create_index('ix_evaluation_runs_status', 'evaluation_runs', ['status'], unique=False)

    # 2. Add columns to evaluations
    op.add_column('evaluations', sa.Column('organization_id', GUID(), nullable=True))
    op.add_column('evaluations', sa.Column('evaluation_run_id', GUID(), nullable=True))
    op.add_column('evaluations', sa.Column('raw_score', sa.Numeric(precision=5, scale=2), nullable=False, server_default='0.0'))
    op.add_column('evaluations', sa.Column('normalized_score', sa.Numeric(precision=5, scale=2), nullable=False, server_default='0.0'))
    op.add_column('evaluations', sa.Column('evidence_coverage', sa.Numeric(precision=5, scale=2), nullable=False, server_default='0.0'))
    op.add_column('evaluations', sa.Column('confidence_level', sa.String(length=30), nullable=False, server_default='HIGH'))
    op.add_column('evaluations', sa.Column('evaluation_status', sa.String(length=30), nullable=False, server_default='COMPLETED'))
    op.add_column('evaluations', sa.Column('scorecard_version', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('evaluations', sa.Column('model_provider', sa.String(length=50), nullable=True))
    op.add_column('evaluations', sa.Column('model_name', sa.String(length=100), nullable=True))
    op.add_column('evaluations', sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=True))

    op.create_foreign_key('fk_evaluations_org_id', 'evaluations', 'organizations', ['organization_id'], ['id'], ondelete='RESTRICT')
    op.create_foreign_key('fk_evaluations_run_id', 'evaluations', 'evaluation_runs', ['evaluation_run_id'], ['id'], ondelete='SET NULL')
    op.create_index('ix_evaluations_org_id', 'evaluations', ['organization_id'], unique=False)
    op.create_index('ix_evaluations_status', 'evaluations', ['evaluation_status'], unique=False)
    op.create_index('ix_evaluations_run_id', 'evaluations', ['evaluation_run_id'], unique=False)

    # 3. Add columns to evaluation_evidence
    op.add_column('evaluation_evidence', sa.Column('awarded_points', sa.Numeric(precision=5, scale=2), nullable=False, server_default='0.0'))
    op.add_column('evaluation_evidence', sa.Column('maximum_points', sa.Numeric(precision=5, scale=2), nullable=False, server_default='0.0'))
    op.add_column('evaluation_evidence', sa.Column('evidence_text', sa.Text(), nullable=True))
    op.add_column('evaluation_evidence', sa.Column('source_reference', sa.String(length=255), nullable=True))
    op.add_column('evaluation_evidence', sa.Column('explanation', sa.Text(), nullable=True))

    # 4. Create recruiter_reviews table
    op.create_table(
        'recruiter_reviews',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('evaluation_id', GUID(), nullable=False),
        sa.Column('recruiter_id', GUID(), nullable=False),
        sa.Column('organization_id', GUID(), nullable=False),
        sa.Column('decision', sa.String(length=30), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['evaluation_id'], ['evaluations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['recruiter_id'], ['users.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_recruiter_reviews_eval_id', 'recruiter_reviews', ['evaluation_id'], unique=False)
    op.create_index('ix_recruiter_reviews_org_id', 'recruiter_reviews', ['organization_id'], unique=False)


def downgrade() -> None:
    op.drop_table('recruiter_reviews')

    op.drop_column('evaluation_evidence', 'explanation')
    op.drop_column('evaluation_evidence', 'source_reference')
    op.drop_column('evaluation_evidence', 'evidence_text')
    op.drop_column('evaluation_evidence', 'maximum_points')
    op.drop_column('evaluation_evidence', 'awarded_points')

    op.drop_index('ix_evaluations_run_id', table_name='evaluations')
    op.drop_index('ix_evaluations_status', table_name='evaluations')
    op.drop_index('ix_evaluations_org_id', table_name='evaluations')
    op.drop_constraint('fk_evaluations_run_id', 'evaluations', type_='foreignkey')
    op.drop_constraint('fk_evaluations_org_id', 'evaluations', type_='foreignkey')
    op.drop_column('evaluations', 'evaluated_at')
    op.drop_column('evaluations', 'model_name')
    op.drop_column('evaluations', 'model_provider')
    op.drop_column('evaluations', 'scorecard_version')
    op.drop_column('evaluations', 'evaluation_status')
    op.drop_column('evaluations', 'confidence_level')
    op.drop_column('evaluations', 'evidence_coverage')
    op.drop_column('evaluations', 'normalized_score')
    op.drop_column('evaluations', 'raw_score')
    op.drop_column('evaluations', 'evaluation_run_id')
    op.drop_column('evaluations', 'organization_id')

    op.drop_table('evaluation_runs')
