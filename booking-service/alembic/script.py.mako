"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    # Extensiones
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    # ENUMs
    service_category = sa.Enum('masaje', 'lavado', 'teñido', 'uñas', 'otro', name='service_category', native_enum=False)
    booking_status = sa.Enum('pending', 'confirmed', 'cancelled', 'completed', 'no_show', name='booking_status', native_enum=False)

    # 1. services
    op.create_table(
        'services',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('nombre', sa.String(120), nullable=False, index=True),
        sa.Column('categoria', service_category, nullable=False),
        sa.Column('descripcion', sa.Text(), nullable=True),
        sa.Column('duracion_min', sa.Integer(), nullable=False),
        sa.Column('precio_clp', sa.Integer(), nullable=False),
        sa.Column('prep_limpieza_min', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('activo', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_check_constraint('ck_service_duracion_positiva', 'services', 'duracion_min > 0')
    op.create_check_constraint('ck_service_precio_no_negativo', 'services', 'precio_clp >= 0')
    op.create_check_constraint('ck_service_prep_no_negativo', 'services', 'prep_limpieza_min >= 0')

    # 2. professionals
    op.create_table(
        'professionals',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('nombre', sa.String(120), nullable=False, index=True),
        sa.Column('google_calendar_id', sa.String(255), nullable=True),
        sa.Column('horario_semanal', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('activo', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )

    # 3. professional_services (N:M)
    op.create_table(
        'professional_services',
        sa.Column('professional_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('professionals.id', ondelete='CASCADE'), nullable=False),
        sa.Column('service_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('services.id', ondelete='CASCADE'), nullable=False),
        sa.Column('orden', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('professional_id', 'service_id', name='uq_professional_service'),
    )

    # 4. business_hours
    op.create_table(
        'business_hours',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('dia_semana', sa.Integer(), nullable=False, unique=True),
        sa.Column('tramos', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('excepciones', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('activo', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_check_constraint('ck_bh_dia_semana', 'business_hours', 'dia_semana BETWEEN 0 AND 6')

    # 5. time_blocks
    op.create_table(
        'time_blocks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('professional_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('professionals.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('inicio', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('fin', sa.DateTime(timezone=True), nullable=False),
        sa.Column('motivo', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_time_blocks_prof_inicio', 'time_blocks', ['professional_id', 'inicio'], postgresql_where=sa.text('professional_id IS NOT NULL'))

    # 6. clients
    op.create_table(
        'clients',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('nombre', sa.String(120), nullable=False),
        sa.Column('telefono', sa.String(30), nullable=False),
        sa.Column('email', sa.String(180), nullable=False, index=True),
        sa.Column('telegram_user_id', sa.BigInteger(), unique=True, nullable=True, index=True),
        sa.Column('consentimiento', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('fecha_alta', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )

    # 7. bookings
    booking_status_enum = sa.Enum('pending', 'confirmed', 'cancelled', 'completed', 'no_show', name='booking_status', native_enum=False)
    op.create_table(
        'bookings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('codigo', sa.String(20), nullable=False, unique=True, index=True),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('clients.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('service_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('services.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('professional_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('professionals.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('inicio', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('fin', sa.DateTime(timezone=True), nullable=False),
        sa.Column('estado', booking_status_enum, nullable=False, server_default='pending'),
        sa.Column('origen', sa.String(50), nullable=False, server_default='telegram'),
        sa.Column('google_event_id', sa.String(255), nullable=True),
        sa.Column('idempotency_key', sa.String(64), nullable=True, unique=True),
        sa.Column('notas', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_check_constraint('ck_booking_fin_post_inicio', 'bookings', 'fin > inicio')
    op.create_index('ix_bookings_client_inicio', 'bookings', ['client_id', 'inicio'])
    op.create_index('ix_bookings_prof_inicio', 'bookings', ['professional_id', 'inicio'], postgresql_where=sa.text('professional_id IS NOT NULL'))
    op.create_index('ix_bookings_estado', 'bookings', ['estado'])

    # 8. conversation_logs
    op.create_table(
        'conversation_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('canal', sa.String(30), nullable=False, index=True),
        sa.Column('usuario_id', sa.String(64), nullable=False, index=True),
        sa.Column('mensajes_resumen', postgresql.JSONB(), nullable=False),
        sa.Column('resultado', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()'), index=True),
    )

    # Triggers para updated_at
    op.execute("""
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END $$;
    """)

    for table in ['services', 'professionals', 'business_hours', 'clients', 'bookings']:
        op.execute(f"""
            CREATE TRIGGER trg_{table}_updated
            BEFORE UPDATE ON {table}
            FOR EACH ROW EXECUTE FUNCTION set_updated_at();
        """)


def downgrade() -> None:
    # Drop triggers
    for table in ['bookings', 'clients', 'business_hours', 'professionals', 'services']:
        op.execute(f'DROP TRIGGER IF EXISTS trg_{table}_updated ON {table}')

    op.execute('DROP FUNCTION IF EXISTS set_updated_at()')

    # Drop tables en orden inverso
    op.drop_table('conversation_logs')
    op.drop_table('bookings')
    op.drop_table('clients')
    op.drop_table('time_blocks')
    op.drop_table('business_hours')
    op.drop_table('professional_services')
    op.drop_table('professionals')
    op.drop_table('services')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS service_category')
    op.execute('DROP TYPE IF EXISTS booking_status')