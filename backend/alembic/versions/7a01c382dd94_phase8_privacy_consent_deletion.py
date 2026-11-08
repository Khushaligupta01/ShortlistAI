"""phase8_privacy_consent_deletion

Revision ID: 7a01c382dd94
Revises: 6f92a341cc43
Create Date: 2026-11-08 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from app.db.base import GUID

# revision identifiers, used by Alembic.
revision = '7a01c382dd94'
down_revision = '6f92a341cc43'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Update candidates table
    op.add_column('candidates', sa.Column('consent_status', sa.String(length=30), nullable=False, server_default='GRANTED'))
    op.add_column('candidates', sa.Column('deletion_status', sa.String(length=30), nullable=True))
    op.create_index('ix_candidates_consent_status', 'candidates', ['consent_status'], unique=False)
    op.create_index('ix_candidates_deletion_status', 'candidates', ['deletion_status'], unique=False)

    # 2. Update consent_records table
    op.add_column('consent_records', sa.Column('status', sa.String(length=30), nullable=False, server_default='GRANTED'))
    op.add_column('consent_records', sa.Column('purpose', sa.String(length=100), nullable=False, server_default='resume_screening_and_shortlisting'))
    op.add_column('consent_records', sa.Column('version', sa.String(length=20), nullable=False, server_default='v1.0'))
    op.add_column('consent_records', sa.Column('collection_method', sa.String(length=50), nullable=False, server_default='DIRECT_NOTICE'))
    op.add_column('consent_records', sa.Column('requisition_id', GUID(), nullable=True))
    op.add_column('consent_records', sa.Column('token_hash', sa.String(length=64), nullable=True))
    op.add_column('consent_records', sa.Column('token_expires_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('consent_records', sa.Column('used_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('consent_records', sa.Column('withdrawn_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('consent_records', sa.Column('withdrawal_reason', sa.Text(), nullable=True))
    op.add_column('consent_records', sa.Column('ip_hash', sa.String(length=64), nullable=True))
    op.add_column('consent_records', sa.Column('user_agent', sa.String(length=255), nullable=True))
    op.add_column('consent_records', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')))
    op.create_foreign_key('fk_consent_records_req_id', 'consent_records', 'requisitions', ['requisition_id'], ['id'], ondelete='SET NULL')
    op.create_index('ix_consent_records_org_id', 'consent_records', ['organization_id'], unique=False)
    op.create_index('ix_consent_records_cand_id', 'consent_records', ['candidate_id'], unique=False)
    op.create_index('ix_consent_records_status', 'consent_records', ['status'], unique=False)
    op.create_index('ix_consent_records_token_hash', 'consent_records', ['token_hash'], unique=False)

    # 3. Create data_requests table
    op.create_table(
        'data_requests',
        sa.Column('id', GUID(), primary_key=True),
        sa.Column('candidate_id', GUID(), sa.ForeignKey('candidates.id', ondelete='CASCADE'), nullable=False),
        sa.Column('organization_id', GUID(), sa.ForeignKey('organizations.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('requested_by', GUID(), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('request_type', sa.String(length=30), nullable=False, server_default='EXPORT'),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='PENDING'),
        sa.Column('export_file_path', sa.String(length=500), nullable=True),
        sa.Column('export_metadata', sa.JSON(), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_data_requests_org_id', 'data_requests', ['organization_id'], unique=False)
    op.create_index('ix_data_requests_candidate_id', 'data_requests', ['candidate_id'], unique=False)
    op.create_index('ix_data_requests_status', 'data_requests', ['status'], unique=False)

    # 4. Create deletion_requests table
    op.create_table(
        'deletion_requests',
        sa.Column('id', GUID(), primary_key=True),
        sa.Column('candidate_id', GUID(), sa.ForeignKey('candidates.id', ondelete='CASCADE'), nullable=False),
        sa.Column('organization_id', GUID(), sa.ForeignKey('organizations.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('requested_by', GUID(), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('reviewer_id', GUID(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='REQUESTED'),
        sa.Column('review_decision', sa.String(length=30), nullable=True),
        sa.Column('review_notes', sa.Text(), nullable=True),
        sa.Column('retention_policy_notes', sa.Text(), nullable=True),
        sa.Column('files_deleted_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_legal_hold', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('legal_hold_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_deletion_requests_org_id', 'deletion_requests', ['organization_id'], unique=False)
    op.create_index('ix_deletion_requests_candidate_id', 'deletion_requests', ['candidate_id'], unique=False)
    op.create_index('ix_deletion_requests_status', 'deletion_requests', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_deletion_requests_status', table_name='deletion_requests')
    op.drop_index('ix_deletion_requests_candidate_id', table_name='deletion_requests')
    op.drop_index('ix_deletion_requests_org_id', table_name='deletion_requests')
    op.drop_table('deletion_requests')

    op.drop_index('ix_data_requests_status', table_name='data_requests')
    op.drop_index('ix_data_requests_candidate_id', table_name='data_requests')
    op.drop_index('ix_data_requests_org_id', table_name='data_requests')
    op.drop_table('data_requests')

    op.drop_index('ix_consent_records_token_hash', table_name='consent_records')
    op.drop_index('ix_consent_records_status', table_name='consent_records')
    op.drop_index('ix_consent_records_cand_id', table_name='consent_records')
    op.drop_index('ix_consent_records_org_id', table_name='consent_records')
    op.drop_constraint('fk_consent_records_req_id', 'consent_records', type_='foreignkey')
    op.drop_column('consent_records', 'updated_at')
    op.drop_column('consent_records', 'user_agent')
    op.drop_column('consent_records', 'ip_hash')
    op.drop_column('consent_records', 'withdrawal_reason')
    op.drop_column('consent_records', 'withdrawn_at')
    op.drop_column('consent_records', 'used_at')
    op.drop_column('consent_records', 'token_expires_at')
    op.drop_column('consent_records', 'token_hash')
    op.drop_column('consent_records', 'requisition_id')
    op.drop_column('consent_records', 'collection_method')
    op.drop_column('consent_records', 'version')
    op.drop_column('consent_records', 'purpose')
    op.drop_column('consent_records', 'status')

    op.drop_index('ix_candidates_deletion_status', table_name='candidates')
    op.drop_index('ix_candidates_consent_status', table_name='candidates')
    op.drop_column('candidates', 'deletion_status')
    op.drop_column('candidates', 'consent_status')
