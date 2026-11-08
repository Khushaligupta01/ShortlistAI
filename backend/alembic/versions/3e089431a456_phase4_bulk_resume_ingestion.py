"""phase4_bulk_resume_ingestion

Revision ID: 3e089431a456
Revises: 0998f7a5da05
Create Date: 2026-11-08 09:14:24.338151

"""
from __future__ import annotations

import os
import sys
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from app.db.base import GUID


# revision identifiers, used by Alembic.
revision: str = '3e089431a456'
down_revision: Union[str, None] = '0998f7a5da05'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Update candidates table
    op.add_column('candidates', sa.Column('total_experience_years', sa.Numeric(precision=4, scale=1), nullable=True))
    op.add_column('candidates', sa.Column('certifications', sa.JSON(), nullable=True))

    # 2. Create candidate_employments table
    op.create_table(
        'candidate_employments',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('candidate_id', GUID(), nullable=False),
        sa.Column('company', sa.String(length=255), nullable=False),
        sa.Column('job_title', sa.String(length=255), nullable=False),
        sa.Column('start_date', sa.String(length=50), nullable=True),
        sa.Column('end_date', sa.String(length=50), nullable=True),
        sa.Column('is_current', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('technologies', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_cand_emp_candidate_id', 'candidate_employments', ['candidate_id'], unique=False)

    # 3. Create candidate_educations table
    op.create_table(
        'candidate_educations',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('candidate_id', GUID(), nullable=False),
        sa.Column('institution', sa.String(length=255), nullable=False),
        sa.Column('qualification', sa.String(length=255), nullable=True),
        sa.Column('field_of_study', sa.String(length=255), nullable=True),
        sa.Column('graduation_year', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_cand_edu_candidate_id', 'candidate_educations', ['candidate_id'], unique=False)

    # 4. Create candidate_skills table
    op.create_table(
        'candidate_skills',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('candidate_id', GUID(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('raw_name', sa.String(length=100), nullable=False),
        sa.Column('evidence', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_cand_skills_candidate_id', 'candidate_skills', ['candidate_id'], unique=False)
    op.create_index('ix_cand_skills_cand_name', 'candidate_skills', ['candidate_id', 'name'], unique=False)

    # 5. Update upload_batches table
    op.add_column('upload_batches', sa.Column('accepted_files', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('upload_batches', sa.Column('rejected_files', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('upload_batches', sa.Column('duplicate_files', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('upload_batches', sa.Column('processing_files', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('upload_batches', sa.Column('completed_files', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('upload_batches', sa.Column('failed_files', sa.Integer(), nullable=False, server_default='0'))
    op.create_index('ix_upload_batches_requisition_id', 'upload_batches', ['requisition_id'], unique=False)

    # 6. Update resumes table
    # Make candidate_id nullable
    op.alter_column('resumes', 'candidate_id', existing_type=GUID(), nullable=True)
    op.add_column('resumes', sa.Column('requisition_id', GUID(), nullable=True))
    op.add_column('resumes', sa.Column('uploaded_by', GUID(), nullable=True))
    op.add_column('resumes', sa.Column('normalized_text', sa.Text(), nullable=True))
    op.add_column('resumes', sa.Column('extraction_status', sa.String(length=30), nullable=False, server_default='pending'))
    op.add_column('resumes', sa.Column('error_code', sa.String(length=50), nullable=True))
    op.add_column('resumes', sa.Column('error_message_safe', sa.Text(), nullable=True))
    op.add_column('resumes', sa.Column('duplicate_of_id', GUID(), nullable=True))
    op.add_column('resumes', sa.Column('duplicate_type', sa.String(length=30), nullable=True))
    op.add_column('resumes', sa.Column('duplicate_details', sa.JSON(), nullable=True))
    op.add_column('resumes', sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True))

    op.create_foreign_key('fk_resumes_requisition_id', 'resumes', 'requisitions', ['requisition_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('fk_resumes_uploaded_by', 'resumes', 'users', ['uploaded_by'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('fk_resumes_duplicate_of_id', 'resumes', 'resumes', ['duplicate_of_id'], ['id'], ondelete='SET NULL')

    op.create_index('ix_resumes_requisition_id', 'resumes', ['requisition_id'], unique=False)
    op.create_index('ix_resumes_org_status', 'resumes', ['organization_id', 'parse_status'], unique=False)
    op.create_index('ix_resumes_duplicate_of_id', 'resumes', ['duplicate_of_id'], unique=False)

    # 7. Create resume_processing_jobs table
    op.create_table(
        'resume_processing_jobs',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('resume_id', GUID(), nullable=False),
        sa.Column('batch_id', GUID(), nullable=False),
        sa.Column('organization_id', GUID(), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='pending'),
        sa.Column('attempt_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_attempts', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_error_code', sa.String(length=50), nullable=True),
        sa.Column('last_error_message', sa.Text(), nullable=True),
        sa.Column('lock_id', sa.String(length=100), nullable=True),
        sa.Column('locked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['batch_id'], ['upload_batches.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['resume_id'], ['resumes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_resume_jobs_status_created', 'resume_processing_jobs', ['status', 'created_at'], unique=False)
    op.create_index('ix_resume_jobs_batch_id', 'resume_processing_jobs', ['batch_id'], unique=False)
    op.create_index('ix_resume_jobs_resume_id', 'resume_processing_jobs', ['resume_id'], unique=False)
    op.create_index('ix_resume_jobs_lock_id', 'resume_processing_jobs', ['lock_id'], unique=False)
    op.create_index('ix_resume_jobs_org_status', 'resume_processing_jobs', ['organization_id', 'status'], unique=False)


def downgrade() -> None:
    op.drop_table('resume_processing_jobs')

    op.drop_index('ix_resumes_duplicate_of_id', table_name='resumes')
    op.drop_index('ix_resumes_org_status', table_name='resumes')
    op.drop_index('ix_resumes_requisition_id', table_name='resumes')

    op.drop_constraint('fk_resumes_duplicate_of_id', 'resumes', type_='foreignkey')
    op.drop_constraint('fk_resumes_uploaded_by', 'resumes', type_='foreignkey')
    op.drop_constraint('fk_resumes_requisition_id', 'resumes', type_='foreignkey')

    op.drop_column('resumes', 'processed_at')
    op.drop_column('resumes', 'duplicate_details')
    op.drop_column('resumes', 'duplicate_type')
    op.drop_column('resumes', 'duplicate_of_id')
    op.drop_column('resumes', 'error_message_safe')
    op.drop_column('resumes', 'error_code')
    op.drop_column('resumes', 'extraction_status')
    op.drop_column('resumes', 'normalized_text')
    op.drop_column('resumes', 'uploaded_by')
    op.drop_column('resumes', 'requisition_id')
    op.alter_column('resumes', 'candidate_id', existing_type=GUID(), nullable=False)

    op.drop_index('ix_upload_batches_requisition_id', table_name='upload_batches')
    op.drop_column('upload_batches', 'failed_files')
    op.drop_column('upload_batches', 'completed_files')
    op.drop_column('upload_batches', 'processing_files')
    op.drop_column('upload_batches', 'duplicate_files')
    op.drop_column('upload_batches', 'rejected_files')
    op.drop_column('upload_batches', 'accepted_files')

    op.drop_table('candidate_skills')
    op.drop_table('candidate_educations')
    op.drop_table('candidate_employments')

    op.drop_column('candidates', 'certifications')
    op.drop_column('candidates', 'total_experience_years')
