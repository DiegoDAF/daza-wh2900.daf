-- Tabla para almacenar el estado de las integraciones (rate limit)
-- Cada servicio guarda su último push para respetar el rate limit

create table if not exists integration_state (
    service_name varchar(50) primary key,
    last_push_time timestamptz not null,
    push_count int default 1,
    last_status varchar(20),  -- 'ok', 'error', 'skipped'
    last_error text,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

comment on table integration_state is 'Estado de integraciones con servicios externos (Weathercloud, etc)';
comment on column integration_state.service_name is 'Nombre del servicio (weathercloud, wunderground, etc)';
comment on column integration_state.last_push_time is 'Timestamp del ultimo push exitoso';
comment on column integration_state.push_count is 'Cantidad total de pushes exitosos';
comment on column integration_state.last_status is 'Estado del ultimo intento (ok, error, skipped)';
comment on column integration_state.last_error is 'Mensaje de error del ultimo intento fallido';
