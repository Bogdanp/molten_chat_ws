"""add Account

Revision ID: d4219ab3e3c4
Revises: 
Create Date: 2018-10-14 11:30:07.786237
"""
import sqlalchemy as sa
from alembic import op


revision = 'd4219ab3e3c4'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('accounts',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(), nullable=False),
    sa.Column('password_hash', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_accounts_username'), 'accounts', ['username'], unique=True)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_accounts_username'), table_name='accounts')
    op.drop_table('accounts')
    # ### end Alembic commands ###
