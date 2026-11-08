"""phase6_candidate_notes

Revision ID: 5e81f129bb32
Revises: 4f19b52a7c81
Create Date: 2026-11-08 10:55:00.000000

"""
from alembic import op
import sqlalchemy as sa
from app.db.base import GUID

# revision identifiers, used by Alembic.
revision = '5e81f129bb32'
down_revision = '4f19b52a7c81'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'candidate_notes',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('candidate_id', GUID(), nullable=False),
        sa.Column('requisition_id', GUID(), nullable=True),
        sa.Column('author_id', GUID(), nullable=False),
        sa.Column('organization_id', GUID(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['requisition_id'], ['requisitions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_candidate_notes_candidate_id', 'candidate_notes', ['candidate_id'], unique=False)
    op.create_index('ix_candidate_notes_org_id', 'candidate_notes', ['organization_id'], unique=False)
    op.create_index('ix_candidate_notes_author_id', 'candidate_notes', ['author_id'], unique=False)
    op.create_index('ix_candidate_notes_requisition_id', 'candidate_notes', ['requisition_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_candidate_notes_requisition_id', table_name='candidate_notes')
    op.drop_index('ix_candidate_notes_author_id', table_name='candidate_notes')
    op.drop_index('ix_candidate_notes_org_id', table_name='candidate_notes')
    op.drop_index('ix_candidate_notes_candidate_id', table_name='candidate_notes')
    op.drop_table('candidate_notes')

