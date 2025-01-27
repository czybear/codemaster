"""add script_unique_id to attend

Revision ID: bed6fe23f09b
Revises: 7b292904ed2f
Create Date: 2024-12-04 09:24:48.893685

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "bed6fe23f09b"
down_revision = "7b292904ed2f"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("ai_course_lesson_attend", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "script_unique_id",
                sa.String(length=36),
                nullable=False,
                comment="Script unique ID",
            )
        )

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("ai_course_lesson_attend", schema=None) as batch_op:
        batch_op.drop_column("script_unique_id")

    # ### end Alembic commands ###
