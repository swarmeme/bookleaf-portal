"""initial schema

Revision ID: ad0f30324e98
Revises: 
Create Date: 2026-10-18 18:42:48.105184

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import app.models.types


# revision identifiers, used by Alembic.
revision: str = 'ad0f30324e98'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('role', sa.Enum('author', 'admin', name='userrole', native_enum=False, length=32), nullable=False),
    sa.Column('created_at', app.models.types.UTCDateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_users_email'), ['email'], unique=True)

    op.create_table('authors',
    sa.Column('id', sa.String(length=16), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('phone', sa.String(length=32), nullable=True),
    sa.Column('city', sa.String(length=128), nullable=True),
    sa.Column('joined_date', sa.Date(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id')
    )
    op.create_table('books',
    sa.Column('id', sa.String(length=16), nullable=False),
    sa.Column('author_id', sa.String(length=16), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('isbn', sa.String(length=32), nullable=False),
    sa.Column('genre', sa.String(length=128), nullable=True),
    sa.Column('publication_date', sa.Date(), nullable=True),
    sa.Column('status', sa.String(length=64), nullable=False),
    sa.Column('mrp', sa.Integer(), nullable=True),
    sa.Column('author_royalty_per_copy', sa.Integer(), nullable=True),
    sa.Column('total_copies_sold', sa.Integer(), nullable=False),
    sa.Column('total_royalty_earned', sa.Integer(), nullable=False),
    sa.Column('royalty_paid', sa.Integer(), nullable=False),
    sa.Column('royalty_pending', sa.Integer(), nullable=False),
    sa.Column('last_royalty_payout_date', sa.Date(), nullable=True),
    sa.Column('print_partner', sa.String(length=64), nullable=True),
    sa.Column('available_on', sa.JSON(), nullable=False),
    sa.ForeignKeyConstraint(['author_id'], ['authors.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('books', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_books_author_id'), ['author_id'], unique=False)

    op.create_table('tickets',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('author_id', sa.String(length=16), nullable=False),
    sa.Column('book_id', sa.String(length=16), nullable=True),
    sa.Column('subject', sa.String(length=200), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('attachment_name', sa.String(length=255), nullable=True),
    sa.Column('status', sa.Enum('open', 'in_progress', 'resolved', 'closed', name='ticketstatus', native_enum=False, length=32), nullable=False),
    sa.Column('assigned_admin_id', sa.Integer(), nullable=True),
    sa.Column('awaiting_team_reply', sa.Boolean(), nullable=False),
    sa.Column('category', sa.Enum('royalty_payments', 'isbn_metadata', 'printing_quality', 'distribution_availability', 'book_status_production', 'general_inquiry', name='ticketcategory', native_enum=False, length=32), nullable=True),
    sa.Column('category_source', sa.Enum('ai', 'fallback', 'admin', name='fieldsource', native_enum=False, length=32), nullable=True),
    sa.Column('priority', sa.Enum('critical', 'high', 'medium', 'low', name='ticketpriority', native_enum=False, length=32), nullable=True),
    sa.Column('priority_source', sa.Enum('ai', 'fallback', 'admin', name='fieldsource', native_enum=False, length=32), nullable=True),
    sa.Column('ai_status', sa.Enum('pending', 'completed', 'failed', 'disabled', name='aistatus', native_enum=False, length=32), nullable=False),
    sa.Column('ai_reasoning', sa.Text(), nullable=True),
    sa.Column('ai_draft', sa.Text(), nullable=True),
    sa.Column('ai_draft_generated_at', app.models.types.UTCDateTime(), nullable=True),
    sa.Column('created_at', app.models.types.UTCDateTime(), nullable=False),
    sa.Column('updated_at', app.models.types.UTCDateTime(), nullable=False),
    sa.Column('first_responded_at', app.models.types.UTCDateTime(), nullable=True),
    sa.Column('resolved_at', app.models.types.UTCDateTime(), nullable=True),
    sa.ForeignKeyConstraint(['assigned_admin_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['author_id'], ['authors.id'], ),
    sa.ForeignKeyConstraint(['book_id'], ['books.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('tickets', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_tickets_author_id'), ['author_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_tickets_awaiting_team_reply'), ['awaiting_team_reply'], unique=False)
        batch_op.create_index(batch_op.f('ix_tickets_category'), ['category'], unique=False)
        batch_op.create_index(batch_op.f('ix_tickets_created_at'), ['created_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_tickets_priority'), ['priority'], unique=False)
        batch_op.create_index(batch_op.f('ix_tickets_status'), ['status'], unique=False)

    op.create_table('internal_notes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('ticket_id', sa.Integer(), nullable=False),
    sa.Column('admin_id', sa.Integer(), nullable=False),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('created_at', app.models.types.UTCDateTime(), nullable=False),
    sa.ForeignKeyConstraint(['admin_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['ticket_id'], ['tickets.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('internal_notes', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_internal_notes_ticket_id'), ['ticket_id'], unique=False)

    op.create_table('ticket_messages',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('ticket_id', sa.Integer(), nullable=False),
    sa.Column('sender_id', sa.Integer(), nullable=False),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('used_ai_draft', sa.Boolean(), nullable=False),
    sa.Column('created_at', app.models.types.UTCDateTime(), nullable=False),
    sa.ForeignKeyConstraint(['sender_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['ticket_id'], ['tickets.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('ticket_messages', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_ticket_messages_ticket_id'), ['ticket_id'], unique=False)



def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('ticket_messages', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_ticket_messages_ticket_id'))

    op.drop_table('ticket_messages')
    with op.batch_alter_table('internal_notes', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_internal_notes_ticket_id'))

    op.drop_table('internal_notes')
    with op.batch_alter_table('tickets', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_tickets_status'))
        batch_op.drop_index(batch_op.f('ix_tickets_priority'))
        batch_op.drop_index(batch_op.f('ix_tickets_created_at'))
        batch_op.drop_index(batch_op.f('ix_tickets_category'))
        batch_op.drop_index(batch_op.f('ix_tickets_awaiting_team_reply'))
        batch_op.drop_index(batch_op.f('ix_tickets_author_id'))

    op.drop_table('tickets')
    with op.batch_alter_table('books', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_books_author_id'))

    op.drop_table('books')
    op.drop_table('authors')
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_users_email'))

    op.drop_table('users')
