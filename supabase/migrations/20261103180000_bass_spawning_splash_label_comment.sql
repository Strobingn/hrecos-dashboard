-- Comment only. The label column stays free text.
comment on column public.detections.label is
  'Detector label, e.g. sturgeon_thunder, drum_knock, toadfish_boatwhistle, bass_spawning_splash, boat, unknown. bass_spawning_splash is surface commotion stored with species_id striped_bass, not a vocalization.';
