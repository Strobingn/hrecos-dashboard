-- Comment only. The label column stays free text.
comment on column public.detections.label is
  'Detector label. Priority order: bass_spawning_splash, sturgeon_thunder, then drum_knock, toadfish_boatwhistle, boat, unknown. bass_spawning_splash is surface commotion stored with species_id striped_bass, not a vocalization. River herring has no detector label.';
