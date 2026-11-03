-- Hudson River fish acoustic monitoring network.
-- Contract tables (schema public): species, hydrophone_nodes, audio_segments,
-- detections, and view detection_counts_hourly.
--
-- Anon and authenticated may read. Inserts and updates go through service_role,
-- which bypasses RLS on Supabase. The audio bucket and the supabase_realtime
-- publication are created when this runs under the Supabase CLI (they are not
-- part of plain Postgres). See docs/fish-network.md.

create extension if not exists pgcrypto;

-- ---------------------------------------------------------------------------
-- Tables
-- ---------------------------------------------------------------------------

create table public.species (
  id text primary key,
  common_name text not null,
  scientific_name text not null,
  soniferous boolean not null,
  freq_low_hz double precision,
  freq_high_hz double precision,
  call_description text,
  season text,
  fishsounds_url text,
  image_url text,
  constraint species_id_not_blank check (char_length(id) > 0),
  constraint species_freq_nonnegative check (
    (freq_low_hz is null or freq_low_hz >= 0)
    and (freq_high_hz is null or freq_high_hz >= 0)
  ),
  constraint species_freq_order check (
    freq_low_hz is null or freq_high_hz is null or freq_high_hz >= freq_low_hz
  )
);

comment on table public.species is
  'Hudson River fishes. soniferous marks species known to make sounds. Frequency columns are a detector band in Hz, not a fish count.';

create table public.hydrophone_nodes (
  id text primary key,
  name text not null,
  lat double precision not null,
  lon double precision not null,
  river_mile numeric(6, 2),
  hardware text,
  sample_rate_hz integer,
  status text not null default 'offline',
  last_heartbeat timestamptz,
  created_at timestamptz not null default now(),
  constraint hydrophone_nodes_id_not_blank check (char_length(id) > 0),
  constraint hydrophone_nodes_status_check check (
    status in ('online', 'offline', 'simulated')
  ),
  constraint hydrophone_nodes_lat_check check (lat >= -90 and lat <= 90),
  constraint hydrophone_nodes_lon_check check (lon >= -180 and lon <= 180),
  constraint hydrophone_nodes_sample_rate_check check (
    sample_rate_hz is null or sample_rate_hz > 0
  ),
  constraint hydrophone_nodes_river_mile_check check (
    river_mile is null or river_mile >= 0
  )
);

comment on table public.hydrophone_nodes is
  'Hydrophone deployments. status is online, offline, or simulated. Realtime is enabled on this table.';

create table public.audio_segments (
  id uuid primary key default gen_random_uuid(),
  node_id text not null references public.hydrophone_nodes (id) on delete restrict,
  start_time timestamptz not null,
  end_time timestamptz not null,
  storage_path text not null,
  rms_db double precision,
  band_levels jsonb,
  created_at timestamptz not null default now(),
  constraint audio_segments_time_check check (end_time >= start_time),
  constraint audio_segments_storage_path_not_blank check (char_length(storage_path) > 0),
  constraint audio_segments_band_levels_object check (
    band_levels is null or jsonb_typeof(band_levels) = 'object'
  )
);

comment on table public.audio_segments is
  'Metadata for a stored hydrophone clip. storage_path is an object key in the public Storage bucket audio, not a full URL. Row contents are public; bytes are read from that bucket.';
comment on column public.audio_segments.band_levels is
  'Band energy in dB, keyed by Hz span, e.g. {"10-100": 42.1, "100-500": 38.0, "500-2000": 31.4}.';

create table public.detections (
  id uuid primary key default gen_random_uuid(),
  node_id text not null references public.hydrophone_nodes (id) on delete restrict,
  segment_id uuid references public.audio_segments (id) on delete set null,
  start_time timestamptz not null,
  end_time timestamptz not null,
  label text not null,
  species_id text references public.species (id) on delete set null,
  confidence double precision,
  model_name text,
  model_version text,
  freq_low_hz double precision,
  freq_high_hz double precision,
  clip_path text,
  review_status text not null default 'unreviewed',
  created_at timestamptz not null default now(),
  constraint detections_time_check check (end_time >= start_time),
  constraint detections_label_not_blank check (char_length(label) > 0),
  constraint detections_confidence_check check (
    confidence is null or (confidence >= 0 and confidence <= 1)
  ),
  constraint detections_review_status_check check (
    review_status in ('unreviewed', 'confirmed', 'rejected')
  ),
  constraint detections_freq_nonnegative check (
    (freq_low_hz is null or freq_low_hz >= 0)
    and (freq_high_hz is null or freq_high_hz >= 0)
  ),
  constraint detections_freq_order check (
    freq_low_hz is null or freq_high_hz is null or freq_high_hz >= freq_low_hz
  )
);

comment on table public.detections is
  'One detected sound event (a call, a boat, or unknown). Not an individual fish. Realtime is enabled on this table.';
comment on column public.detections.label is
  'Detector label, e.g. sturgeon_thunder, drum_knock, toadfish_boatwhistle, boat, unknown.';
comment on column public.detections.clip_path is
  'Object key in the Storage bucket audio for the extracted clip. Null when no clip was saved.';
comment on column public.detections.review_status is
  'unreviewed, confirmed, or rejected. Rejected rows stay in the table but are left out of detection_counts_hourly.';

-- ---------------------------------------------------------------------------
-- Indexes (time columns, foreign keys, hourly aggregation)
-- ---------------------------------------------------------------------------

create index hydrophone_nodes_last_heartbeat_idx
  on public.hydrophone_nodes (last_heartbeat desc);

create index audio_segments_start_time_idx
  on public.audio_segments (start_time desc);

create index audio_segments_end_time_idx
  on public.audio_segments (end_time desc);

create index audio_segments_created_at_idx
  on public.audio_segments (created_at desc);

create index audio_segments_node_start_idx
  on public.audio_segments (node_id, start_time desc);

create index detections_start_time_idx
  on public.detections (start_time desc);

create index detections_end_time_idx
  on public.detections (end_time desc);

create index detections_created_at_idx
  on public.detections (created_at desc);

create index detections_node_start_idx
  on public.detections (node_id, start_time desc);

create index detections_species_start_idx
  on public.detections (species_id, start_time desc);

create index detections_segment_id_idx
  on public.detections (segment_id);

create index detections_label_start_idx
  on public.detections (label, start_time desc);

create index detections_unreviewed_idx
  on public.detections (created_at desc)
  where review_status = 'unreviewed';

-- Matches the UTC hour expression in detection_counts_hourly.
create index detections_hourly_activity_idx
  on public.detections (
    node_id,
    species_id,
    label,
    ((date_trunc('hour', start_time at time zone 'UTC') at time zone 'UTC'))
  )
  where review_status <> 'rejected';

-- ---------------------------------------------------------------------------
-- Calling activity per UTC hour. Not a count of fish.
-- security_invoker so the underlying detections SELECT policy applies.
-- ---------------------------------------------------------------------------

create view public.detection_counts_hourly
with (security_invoker = true) as
select
  d.node_id,
  d.species_id,
  d.label,
  (date_trunc('hour', d.start_time at time zone 'UTC') at time zone 'UTC') as hour,
  count(*)::bigint as detections,
  avg(d.confidence) as avg_confidence
from public.detections d
where d.review_status <> 'rejected'
group by
  d.node_id,
  d.species_id,
  d.label,
  (date_trunc('hour', d.start_time at time zone 'UTC') at time zone 'UTC');

comment on view public.detection_counts_hourly is
  'Calling activity per UTC hour: number of non-rejected detection events for a node, species, and label. Not an individual-fish count. hour is the UTC hour start.';

-- ---------------------------------------------------------------------------
-- Roles. Supabase already has these; create them only on plain Postgres
-- so the grants below have a target. service_role bypasses RLS.
-- ---------------------------------------------------------------------------

do $roles$
begin
  if not exists (select 1 from pg_roles where rolname = 'anon') then
    create role anon nologin;
  end if;
  if not exists (select 1 from pg_roles where rolname = 'authenticated') then
    create role authenticated nologin;
  end if;
  if not exists (select 1 from pg_roles where rolname = 'service_role') then
    create role service_role nologin bypassrls;
  end if;
end
$roles$;

grant usage on schema public to anon, authenticated, service_role;

-- Cloud projects grant every privilege to anon by default. Take the writes
-- back, then grant read only. service_role keeps read and write and bypasses RLS.
revoke all privileges on table
  public.species,
  public.hydrophone_nodes,
  public.audio_segments,
  public.detections
from public, anon, authenticated;

grant select on table
  public.species,
  public.hydrophone_nodes,
  public.audio_segments,
  public.detections
to anon, authenticated;

grant select, insert, update, delete on table
  public.species,
  public.hydrophone_nodes,
  public.audio_segments,
  public.detections
to service_role;

revoke all privileges on table public.detection_counts_hourly from public, anon, authenticated;
grant select on table public.detection_counts_hourly to anon, authenticated, service_role;

alter table public.species enable row level security;
alter table public.hydrophone_nodes enable row level security;
alter table public.audio_segments enable row level security;
alter table public.detections enable row level security;

create policy species_public_read
  on public.species
  for select
  to anon, authenticated
  using (true);

create policy hydrophone_nodes_public_read
  on public.hydrophone_nodes
  for select
  to anon, authenticated
  using (true);

create policy audio_segments_public_read
  on public.audio_segments
  for select
  to anon, authenticated
  using (true);

create policy detections_public_read
  on public.detections
  for select
  to anon, authenticated
  using (true);

-- No insert, update, or delete policies. Client roles cannot write.
-- service_role has bypassrls, so it does not need a write policy.

-- ---------------------------------------------------------------------------
-- Realtime. Full replica identity so update and delete events include the
-- previous row. The publication exists only on Supabase.
-- ---------------------------------------------------------------------------

alter table public.detections replica identity full;
alter table public.hydrophone_nodes replica identity full;

do $realtime$
begin
  if not exists (select 1 from pg_publication where pubname = 'supabase_realtime') then
    if exists (select 1 from pg_namespace where nspname = 'auth') then
      raise exception 'auth schema is present but publication supabase_realtime is missing';
    end if;
    raise notice 'publication supabase_realtime not installed; skipped Realtime. Apply this migration with the Supabase CLI.';
    return;
  end if;

  if not exists (
    select 1
    from pg_publication_tables
    where pubname = 'supabase_realtime'
      and schemaname = 'public'
      and tablename = 'detections'
  ) then
    alter publication supabase_realtime add table public.detections;
  end if;

  if not exists (
    select 1
    from pg_publication_tables
    where pubname = 'supabase_realtime'
      and schemaname = 'public'
      and tablename = 'hydrophone_nodes'
  ) then
    alter publication supabase_realtime add table public.hydrophone_nodes;
  end if;
end
$realtime$;

-- ---------------------------------------------------------------------------
-- Storage bucket audio, public read. Object writes stay on service_role
-- (no insert/update/delete policy for client roles).
-- ---------------------------------------------------------------------------

do $storage$
begin
  if to_regclass('storage.buckets') is null or to_regclass('storage.objects') is null then
    if exists (select 1 from pg_namespace where nspname = 'auth') then
      raise exception 'auth schema is present but storage.buckets is missing';
    end if;
    raise notice 'storage schema not installed; skipped audio bucket. Apply this migration with the Supabase CLI.';
    return;
  end if;

  insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
  values (
    'audio',
    'audio',
    true,
    104857600,
    array[
      'audio/wav',
      'audio/x-wav',
      'audio/wave',
      'audio/vnd.wave',
      'audio/mpeg',
      'audio/flac',
      'audio/ogg',
      'audio/webm',
      'audio/mp4',
      'application/octet-stream'
    ]::text[]
  )
  on conflict (id) do update
    set name = excluded.name,
        public = excluded.public,
        file_size_limit = excluded.file_size_limit,
        allowed_mime_types = excluded.allowed_mime_types;

  drop policy if exists audio_public_read on storage.objects;
  create policy audio_public_read
    on storage.objects
    for select
    to anon, authenticated
    using (bucket_id = 'audio');
end
$storage$;
