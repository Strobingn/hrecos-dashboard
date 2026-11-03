-- Follow-up to 20261103160000_sonar_fish_passage.sql.
-- Adds the instrument source and a direction for logs that do not observe
-- along-river heading. Does not rewrite the earlier migration.

alter table public.sonar_tracks
  add column source text not null default 'synthetic';

alter table public.sonar_tracks
  add constraint sonar_tracks_source_check check (
    source in ('synthetic', 'lowrance_log', 'aris', 'split_beam')
  );

comment on column public.sonar_tracks.source is
  'Where the track came from. synthetic is the edge simulator. lowrance_log is a .sl2 or .sl3 import. aris and split_beam are reserved for a later recorder. Unclassified lowrance_log rows keep species_id null and stay out of fish_passage_hourly.';

alter table public.sonar_tracks
  drop constraint sonar_tracks_direction_check;

alter table public.sonar_tracks
  add constraint sonar_tracks_direction_check check (
    direction in ('upstream', 'downstream', 'milling', 'unknown')
  );

comment on column public.sonar_tracks.direction is
  'upstream, downstream, milling, or unknown. Milling is a track that reverses or circles in a horizontal beam, including a striped bass surface cluster. unknown is a down-looking or side-looking consumer log that does not measure along-river heading.';

comment on column public.sonar_tracks.features is
  'Track summary. Synthetic rows set synthetic=true. Lowrance imports set detector, detection_confidence, size_class, and bass_candidate. detection_confidence is not a species probability. species_id stays null until a later model or a reviewer assigns it.';
