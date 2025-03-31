"""initial migration

Revision ID: c19f0a0bedd2
Revises: 
Create Date: 2025-03-31 14:18:54.361079

"""
from alembic import op
import sqlalchemy as sa
revision = 'c19f0a0bedd2'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('users', sa.Column('id', sa.String(length=36), nullable=False), sa.Column('username', sa.String(length=64), nullable=False), sa.Column('email', sa.String(length=120), nullable=False), sa.Column('password_hash', sa.String(length=256), nullable=False), sa.Column('created_at', sa.DateTime(), nullable=True), sa.Column('last_login', sa.DateTime(), nullable=True), sa.PrimaryKeyConstraint('id'), sa.UniqueConstraint('email'), sa.UniqueConstraint('username'))
    op.create_table('files', sa.Column('id', sa.String(length=36), nullable=False), sa.Column('filename', sa.String(length=255), nullable=False), sa.Column('upload_time', sa.DateTime(), nullable=True), sa.Column('status', sa.String(length=50), nullable=True), sa.Column('error_message', sa.Text(), nullable=True), sa.Column('current_stage', sa.String(length=50), nullable=True), sa.Column('progress_percent', sa.Float(), nullable=True), sa.Column('stage_progress', sa.Float(), nullable=True), sa.Column('blob_url', sa.String(length=512), nullable=True), sa.Column('transcript_url', sa.String(length=512), nullable=True), sa.Column('transcription_id', sa.String(length=255), nullable=True), sa.Column('duration_seconds', sa.String(length=50), nullable=True), sa.Column('speaker_count', sa.String(length=10), nullable=True), sa.Column('user_id', sa.String(length=36), nullable=True), sa.ForeignKeyConstraint(['user_id'], ['users.id']), sa.PrimaryKeyConstraint('id'))

def downgrade():
    op.drop_table('files')
    op.drop_table('users')