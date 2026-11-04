-- Sonar passage track for the Hudson River fish network.
-- Contract: sonar_nodes, sonar_tracks, fish_passage_hourly,
-- striped_bass_passage_and_calls_hourly.
--
-- fish_passage_hourly.fish_count is a count of tracks, one accepted track
-- per fish that passed through the beam. It is not calling activity.
-- detection_counts_hourly remains a count of sound events.
--
-- Anon and authenticated may read. Inserts and updates go through service_role.
-- The sonar bucket and the supabase_realtime publication are created when this
-- runs under the Supabase CLI. See docs/sonar-track.md.

-- ---------------------------------------------------------------------------
-- Tables
-- ---------------------------------------------------------------------------

create table public.sonar_nodes (
  id text primary key,
  name text not null,
  lat double precision not null,
  lon double precision not null,
  river_mile numeric(6, 2),
  hardware text,
  status text not null default 'offline',
  last_heartbeat timestamptz,
  created_at timestamptz not null default now(),
  constraint sonar_nodes_id_not_blank check (char_length(id) > 0),
  constraint sonar_nodes_status_check check (
    status in ('online', 'offline', 'simulated')
  ),
  constraint sonar_nodes_lat_check check (lat >= -90 and lat <= 90),
  constraint sonar_nodes_lon_check check (lon >= -180 and lon <= 180),
  constraint sonar_nodes_river_mile_check check (
    river_mile is null or river_mile >= 0
  )
);

comment on table public.sonar_nodes is
  'Imaging-sonar or split-beam deployments. id is the same site slug as hydrophone_nodes when both instruments share a bank (westpoint-cornwall), but there is no foreign key: a sonar can exist without a hydrophone. status is online, offline, or simulated.';

create table public.sonar_tracks (
  id uuid primary key default gen_random_uuid(),
  node_id text not null references public.sonar_nodes (id) on delete restrict,
  start_time timestamptz not null,
  end_time timestamptz not null,
  direction text not null,
  length_cm double precision,
  depth_m double precision,
  range_m double precision,
  speed_mps double precision,
  species_id text references public.species (id) on delete set null,
  species_confidence double precision,
  model_name text,
  model_version text,
  review_status text not null default 'unreviewed',
  clip_path text,
  features jsonb,
  created_at timestamptz not null default now(),
  constraint sonar_tracks_time_check check (end_time >= start_time),
  constraint sonar_tracks_direction_check check (
    direction in ('upstream', 'downstream', 'milling')
  ),
  constraint sonar_tracks_length_check check (
    length_cm is null or length_cm > 0
  ),
  constraint sonar_tracks_depth_check check (
    depth_m is null or depth_m >= 0
  ),
  constraint sonar_tracks_range_check check (
    range_m is null or range_m >= 0
  ),
  constraint sonar_tracks_speed_check check (
    speed_mps is null or speed_mps >= 0
  ),
  constraint sonar_tracks_confidence_check check (
    species_confidence is null
    or (species_confidence >= 0 and species_confidence <= 1)
  ),
  constraint sonar_tracks_review_status_check check (
    review_status in ('unreviewed', 'confirmed', 'rejected')
  ),
  constraint sonar_tracks_features_object check (
    features is null or jsonb_typeof(features) = 'object'
  )
);

comment on table public.sonar_tracks is
  'One tracked target that passed through the sonar beam. One row is one fish only after review; until then it is one track. Not a sound event. Realtime is enabled on this table.';
comment on column public.sonar_tracks.direction is
  'upstream, downstream, or milling. Milling is a track that reverses or circles in the beam, including a striped bass surface cluster during the spawn.';
comment on column public.sonar_tracks.speed_mps is
  'Along-beam or along-track speed in metres per second. The column is the speed field of the sonar track contract.';
comment on column public.sonar_tracks.species_confidence is
  'Classifier score from 0 to 1. A heuristic rank, not a calibrated probability, unless the model card says otherwise.';
comment on column public.sonar_tracks.clip_path is
  'Object key in the Storage bucket sonar. Null when no clip was saved. Synthetic runs store a JSON sidecar, not an ARIS frame.';
comment on column public.sonar_tracks.features is
  'Track summary used by the classifier: behavior, cluster_size, near_surface, cluster_id, synthetic. Not a substitute for an ARIS frame.';
comment on column public.sonar_tracks.review_status is
  'unreviewed, confirmed, or rejected. Rejected rows stay in the table and are left out of fish_passage_hourly.';

-- ---------------------------------------------------------------------------
-- Indexes
-- ---------------------------------------------------------------------------

create index sonar_nodes_last_heartbeat_idx
  on public.sonar_nodes (last_heartbeat desc);

create index sonar_tracks_start_time_idx
  on public.sonar_tracks (start_time desc);

create index sonar_tracks_node_start_idx
  on public.sonar_tracks (node_id, start_time desc);

create index sonar_tracks_species_start_idx
  on public.sonar_tracks (species_id, start_time desc);

create index sonar_tracks_unreviewed_idx
  on public.sonar_tracks (created_at desc)
  where review_status = 'unreviewed';

create index sonar_tracks_hourly_idx
  on public.sonar_tracks (
    node_id,
    species_id,
    direction,
    ((date_trunc('hour', start_time at time zone 'UTC') at time zone 'UTC'))
  )
  where review_status <> 'rejected';

-- ---------------------------------------------------------------------------
-- Individual fish (tracks) per UTC hour.
-- Null species_id is excluded: an unclassified target is not a species count.
-- ---------------------------------------------------------------------------

create view public.fish_passage_hourly
with (security_invoker = true) as
select
  t.node_id,
  t.species_id,
  t.direction,
  (date_trunc('hour', t.start_time at time zone 'UTC') at time zone 'UTC') as hour,
  count(*)::bigint as fish_count,
  avg(t.length_cm) as mean_length_cm
from public.sonar_tracks t
where t.review_status <> 'rejected'
  and t.species_id is not null
group by
  t.node_id,
  t.species_id,
  t.direction,
  (date_trunc('hour', t.start_time at time zone 'UTC') at time zone 'UTC');

comment on view public.fish_passage_hourly is
  'Individual fish per UTC hour: non-rejected sonar tracks with a species, grouped by node, species, and direction. fish_count is a track count, not calling activity. Unclassified tracks are omitted. hour is the UTC hour start. mean_length_cm is the mean of length_cm and is null when every length in the group is null.';

-- ---------------------------------------------------------------------------
-- Striped bass: sonar passage joined to hydrophone calling activity.
-- splash_detections and striped_bass_detections are hour-level totals.
-- They repeat on each direction row. Do not sum them across directions.
-- ---------------------------------------------------------------------------

create view public.striped_bass_passage_and_calls_hourly
with (security_invoker = true) as
with passage as (
  select
    node_id,
    direction,
    hour,
    fish_count,
    mean_length_cm
  from public.fish_passage_hourly
  where species_id = 'striped_bass'
),
calls as (
  select
    node_id,
    hour,
    coalesce(
      sum(detections) filter (where label = 'bass_spawning_splash'),
      0
    )::bigint as splash_detections,
    coalesce(
      sum(detections) filter (where species_id = 'striped_bass'),
      0
    )::bigint as striped_bass_detections
  from public.detection_counts_hourly
  group by node_id, hour
  having coalesce(sum(detections) filter (where label = 'bass_spawning_splash'), 0) > 0
      or coalesce(sum(detections) filter (where species_id = 'striped_bass'), 0) > 0
)
select
  coalesce(p.node_id, c.node_id) as node_id,
  coalesce(p.hour, c.hour) as hour,
  p.direction,
  p.fish_count,
  p.mean_length_cm,
  coalesce(c.splash_detections, 0)::bigint as splash_detections,
  coalesce(c.striped_bass_detections, 0)::bigint as striped_bass_detections
from passage p
full outer join calls c
  on p.node_id = c.node_id
 and p.hour = c.hour;

comment on view public.striped_bass_passage_and_calls_hourly is
  'Striped bass sonar passage (fish_count, per direction) beside hydrophone activity in the same UTC hour. splash_detections counts bass_spawning_splash events. striped_bass_detections counts every detection with species_id striped_bass, so a splash labeled that way is inside both numbers. Both detection totals are for the hour and are repeated on every direction row; summing them across directions double-counts. A hydrophone-only hour has null direction and null fish_count. A sonar-only hour has zero detection totals.';

-- ---------------------------------------------------------------------------
-- Roles. Created only when this database does not already have them.
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

revoke all privileges on table
  public.sonar_nodes,
  public.sonar_tracks
from public, anon, authenticated;

grant select on table
  public.sonar_nodes,
  public.sonar_tracks
to anon, authenticated;

grant select, insert, update, delete on table
  public.sonar_nodes,
  public.sonar_tracks
to service_role;

revoke all privileges on table
  public.fish_passage_hourly,
  public.striped_bass_passage_and_calls_hourly
from public, anon, authenticated;

grant select on table
  public.fish_passage_hourly,
  public.striped_bass_passage_and_calls_hourly
to anon, authenticated, service_role;

alter table public.sonar_nodes enable row level security;
alter table public.sonar_tracks enable row level security;

create policy sonar_nodes_public_read
  on public.sonar_nodes
  for select
  to anon, authenticated
  using (true);

create policy sonar_tracks_public_read
  on public.sonar_tracks
  for select
  to anon, authenticated
  using (true);

-- ---------------------------------------------------------------------------
-- Realtime
-- ---------------------------------------------------------------------------

alter table public.sonar_nodes replica identity full;
alter table public.sonar_tracks replica identity full;

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
      and tablename = 'sonar_nodes'
  ) then
    alter publication supabase_realtime add table public.sonar_nodes;
  end if;

  if not exists (
    select 1
    from pg_publication_tables
    where pubname = 'supabase_realtime'
      and schemaname = 'public'
      and tablename = 'sonar_tracks'
  ) then
    alter publication supabase_realtime add table public.sonar_tracks;
  end if;
end
$realtime$;

-- ---------------------------------------------------------------------------
-- Storage bucket sonar, public read. Synthetic clips are JSON. A later ARIS
-- recorder may store png or mp4 under the same key space.
-- ---------------------------------------------------------------------------

do $storage$
begin
  if to_regclass('storage.buckets') is null or to_regclass('storage.objects') is null then
    if exists (select 1 from pg_namespace where nspname = 'auth') then
      raise exception 'auth schema is present but storage.buckets is missing';
    end if;
    raise notice 'storage schema not installed; skipped sonar bucket. Apply this migration with the Supabase CLI.';
    return;
  end if;

  insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
  values (
    'sonar',
    'sonar',
    true,
    104857600,
    array[
      'application/json',
      'image/png',
      'image/jpeg',
      'video/mp4',
      'application/octet-stream'
    ]::text[]
  )
  on conflict (id) do update
    set name = excluded.name,
        public = excluded.public,
        file_size_limit = excluded.file_size_limit,
        allowed_mime_types = excluded.allowed_mime_types;

  drop policy if exists sonar_public_read on storage.objects;
  create policy sonar_public_read
    on storage.objects
    for select
    to anon, authenticated
    using (bucket_id = 'sonar');
end
$storage$;

-- ---------------------------------------------------------------------------
-- Seeded simulated node. Same coordinates as the hydrophone seed.
-- Poughkeepsie and Tappan Zee are not seeded; they are later sites.
-- ---------------------------------------------------------------------------

insert into public.sonar_nodes (
  id,
  name,
  lat,
  lon,
  river_mile,
  hardware,
  status,
  last_heartbeat
) values (
  'westpoint-cornwall',
  'West Point / Cornwall',
  41.4150,
  -73.9600,
  54.0,
  'Simulated ARIS Explorer-class imaging sonar (no instrument connected)',
  'simulated',
  now()
)
on conflict (id) do update set
  name = excluded.name,
  lat = excluded.lat,
  lon = excluded.lon,
  river_mile = excluded.river_mile,
  hardware = excluded.hardware,
  status = excluded.status,
  last_heartbeat = excluded.last_heartbeat;
