"""phase7_client_portal_and_pipeline

Revision ID: 6f92a341cc43
Revises: 5e81f129bb32
Create Date: 2026-11-08 11:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from app.db.base import GUID

# revision identifiers, used by Alembic.
revision = '6f92a341cc43'
down_revision = '5e81f129bb32'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Update submissions table
    op.add_column('submissions', sa.Column('current_stage', sa.String(length=50), nullable=False, server_default='SUBMITTED'))
    op.add_column('submissions', sa.Column('recruiter_notes_for_client', sa.Text(), nullable=True))
    op.add_column('submissions', sa.Column('custom_candidate_reference', sa.String(length=50), nullable=True))
    op.create_index('ix_submissions_current_stage', 'submissions', ['current_stage'], unique=False)

    # 2. Update requisitions table
    op.add_column('requisitions', sa.Column('client_organization_id', GUID(), nullable=True))
    op.create_foreign_key('fk_requisitions_client_org_id', 'requisitions', 'organizations', ['client_organization_id'], ['id'], ondelete='SET NULL')
    op.create_index('ix_requisitions_client_org_id', 'requisitions', ['client_organization_id'], unique=False)

    # 3. Create client_requests table
    op.create_table(
        'client_requests',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('submission_id', GUID(), nullable=False),
        sa.Column('client_organization_id', GUID(), nullable=False),
        sa.Column('requested_by', GUID(), nullable=False),
        sa.Column('request_type', sa.String(length=50), nullable=False),
        sa.Column('details', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='PENDING'),
        sa.Column('recruiter_response', sa.Text(), nullable=True),
        sa.Column('responded_by', GUID(), nullable=True),
        sa.Column('responded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['client_organization_id'], ['organizations.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['requested_by'], ['users.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['responded_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['submission_id'], ['submissions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_client_requests_client_org_id', 'client_requests', ['client_organization_id'], unique=False)
    op.create_index('ix_client_requests_status', 'client_requests', ['status'], unique=False)
    op.create_index('ix_client_requests_submission_id', 'client_requests', ['submission_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_client_requests_submission_id', table_name='client_requests')
    op.drop_index('ix_client_requests_status', table_name='client_requests')
    op.drop_index('ix_client_requests_client_org_id', table_name='client_requests')
    op.drop_table('client_requests')

    op.drop_index('ix_requisitions_client_org_id', table_name='requisitions')
    op.drop_constraint('fk_requisitions_client_org_id', 'requisitions', type_='foreignkey')
    op.drop_column('requisitions', 'client_organization_id')

    op.drop_index('ix_submissions_current_stage', table_name='submissions')
    op.drop_column('submissions', 'custom_candidate_reference')
    op.drop_column('submissions', 'recruiter_notes_for_client')
    op.drop_column('submissions', 'current_stage')
