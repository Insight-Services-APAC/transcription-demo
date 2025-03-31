"""initial migration

Revision ID: 7074c1d16a4e
Revises: 
Create Date: 2025-03-27 14:21:56.902635

"""
from alembic import op
import sqlalchemy as sa
revision = '7074c1d16a4e'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('files', sa.Column('id', sa.String(length=36), nullable=False), sa.Column('filename', sa.String(length=255), nullable=False), sa.Column('upload_time', sa.DateTime(), nullable=True), sa.Column('status', sa.String(length=50), nullable=True), sa.Column('error_message', sa.Text(), nullable=True), sa.Column('current_stage', sa.String(length=50), nullable=True), sa.Column('progress_percent', sa.Float(), nullable=True), sa.Column('stage_progress', sa.Float(), nullable=True), sa.Column('blob_url', sa.String(length=512), nullable=True), sa.Column('transcript_url', sa.String(length=512), nullable=True), sa.Column('transcription_id', sa.String(length=255), nullable=True), sa.Column('duration_seconds', sa.String(length=50), nullable=True), sa.Column('speaker_count', sa.String(length=10), nullable=True), sa.PrimaryKeyConstraint('id'))

def downgrade():
    op.drop_table('files')