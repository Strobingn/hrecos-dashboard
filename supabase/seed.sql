-- Seed for the Hudson River fish acoustic network.
-- Species notes are reference facts for the detector and the UI.
-- Hydrophone rows are simulated nodes in the focus reach, not live hardware.
-- Safe to re-run: conflicts update the seeded columns.

insert into public.species (
  id,
  common_name,
  scientific_name,
  soniferous,
  freq_low_hz,
  freq_high_hz,
  call_description,
  season,
  fishsounds_url,
  image_url
) values
  (
    'atlantic_sturgeon',
    'Atlantic sturgeon',
    'Acipenser oxyrinchus',
    true,
    10,
    100,
    'Spawning thunder: a short series of low-frequency percussive beats. Field recordings at the Hyde Park, NY spawning reach in June and July 2021 had a median peak frequency of 44 Hz, with most energy between 10 and 100 Hz (Cohen et al., Endangered Species Research 58, 2025). A detection is one thunder, not one fish.',
    'Late spring to early summer. Hudson spawning run; thunders recorded June to early July at Hyde Park and were absent in April pre-spawn monitoring.',
    'https://fishsounds.net/results-fish.js?query=Acipenser%20oxyrinchus',
    'https://upload.wikimedia.org/wikipedia/commons/6/65/Acipenser_oxyrhynchus_%28edit%29.png'
  ),
  (
    'freshwater_drum',
    'Freshwater drum',
    'Aplodinotus grunniens',
    true,
    350,
    450,
    'Knock trains during chorusing. A survey of the New York State Canal System, the route of the Hudson invasion, reported trains of about 1 to 119 knocks with a mean peak frequency of 400 Hz (Journal of the Acoustical Society of America 141, 2017, doi:10.1121/1.4988961). The stored band is a +/- 50 Hz window around that reported mean peak, not a measured spectrum limit. Choruses can last for hours. Counts are calling activity, not abundance.',
    'June to July chorusing in the tidal Hudson.',
    'https://fishsounds.net/results-fish.js?query=Aplodinotus%20grunniens',
    'https://upload.wikimedia.org/wikipedia/commons/f/fb/Aplodinotus_grunniens.jpg'
  ),
  (
    'oyster_toadfish',
    'Oyster toadfish',
    'Opsanus tau',
    true,
    100,
    250,
    'Male boatwhistle advertisement call, a tonal signal whose fundamental commonly sits near 100 to 250 Hz and shifts with temperature. Harmonics extend above that fundamental. Anderson, Rountree, and Juanes (Transactions of the American Fisheries Society, 2008) identified the species in Hudson recordings near the river mouth.',
    'Late spring through summer in the saline lower estuary.',
    'https://fishsounds.net/results-fish.js?query=Opsanus%20tau',
    'https://upload.wikimedia.org/wikipedia/commons/8/84/Opsanus_tau.jpg'
  ),
  (
    'weakfish',
    'Weakfish',
    'Cynoscion regalis',
    true,
    null,
    null,
    'Pulsed swim-bladder drumming used in courtship. Dominant frequency is typically a few hundred hertz and is lower in larger fish. A single Hudson peak frequency is not stored. Present as a caller in the saline lower estuary rather than the freshwater tidal reach.',
    'Late spring and summer in the saline lower estuary.',
    'https://fishsounds.net/results-fish.js?query=Cynoscion%20regalis',
    'https://upload.wikimedia.org/wikipedia/commons/1/1e/FMIB_51963_Squeteague-_Weakfish_%28Cynoscion_regalis%29.jpeg'
  ),
  (
    'channel_catfish',
    'Channel catfish',
    'Ictalurus punctatus',
    true,
    null,
    null,
    'Pectoral-spine stridulation and swim-bladder sounds. Identified in Hudson River recordings, including the Tivoli Bays work of Anderson, Rountree, and Juanes (2008). Energy spans low-frequency drumming and higher-frequency stridulation, so no single band is stored.',
    'Warm season in the freshwater tidal Hudson.',
    'https://fishsounds.net/results-fish.js?query=Ictalurus%20punctatus',
    'https://upload.wikimedia.org/wikipedia/commons/2/28/Ictalurus_punctatus.jpg'
  ),
  (
    'brown_bullhead',
    'Brown bullhead',
    'Ameiurus nebulosus',
    true,
    null,
    null,
    'Pectoral-spine stridulation. Identified from Hudson River recordings by Anderson, Rountree, and Juanes (2008). The sound is broadband, so no single peak band is stored.',
    'Warm season in the freshwater tidal Hudson.',
    'https://fishsounds.net/results-fish.js?query=Ameiurus%20nebulosus',
    'https://upload.wikimedia.org/wikipedia/commons/b/b4/Ameiurus_nebulosus.jpg'
  ),
  (
    'striped_cusk_eel',
    'Striped cusk-eel',
    'Ophidion marginatum',
    true,
    null,
    null,
    'Nocturnal chatter, often heard as a jackhammer chorus and higher in frequency than sturgeon thunder or drum knocks. Identified in Hudson River recordings by Anderson, Rountree, and Juanes (2008). A single numeric band is not stored.',
    'Summer nights in the saline lower estuary.',
    'https://fishsounds.net/results-fish.js?query=Ophidion%20marginatum',
    'https://upload.wikimedia.org/wikipedia/commons/5/56/Striped_cusk-eel.jpg'
  ),
  (
    'striped_bass',
    'Striped bass',
    'Morone saxatilis',
    false,
    null,
    null,
    'No confirmed species-specific vocalization. The detector label bass_spawning_splash is surface splashing from spawning rock fights (several males bumping a female at the surface), not a call, and is stored with this species_id. No published spectrum of that splash was found (behavior in Setzler et al. 1980, NOAA Tech. Rep. NMFS Circ. 433).',
    'Hudson spawning is roughly late April through June in water near 14-20 C, on reaches above Kingston and through West Point-Poughkeepsie, often in the evening and at night. Also resident and migratory in the tidal Hudson.',
    'https://fishsounds.net/results-fish.js?query=Morone%20saxatilis',
    'https://upload.wikimedia.org/wikipedia/commons/7/74/Morone_saxatilis_SI2.jpg'
  ),
  (
    'american_shad',
    'American shad',
    'Alosa sapidissima',
    false,
    null,
    null,
    'No confirmed calls. Included as a non-soniferous reference for the spring spawning run.',
    'Spring spawning run in the tidal Hudson.',
    'https://fishsounds.net/results-fish.js?query=Alosa%20sapidissima',
    'https://upload.wikimedia.org/wikipedia/commons/e/ef/Alosa_sapidissima.jpg'
  ),
  (
    'river_herring',
    'River herring',
    'Alosa pseudoharengus / Alosa aestivalis',
    false,
    null,
    null,
    'Alewife and blueback herring, treated here as one reference row. No confirmed calls. The image is an alewife (Alosa pseudoharengus).',
    'Spring spawning runs in the tidal Hudson.',
    'https://fishsounds.net/results-fish.js?query=Alosa',
    'https://upload.wikimedia.org/wikipedia/commons/f/fc/Alosa_pseudoharengus.jpg'
  ),
  (
    'american_eel',
    'American eel',
    'Anguilla rostrata',
    false,
    null,
    null,
    'No confirmed calls. Catadromous Hudson resident, included as a non-soniferous reference.',
    'Present year-round; adults leave for the Sargasso Sea in fall.',
    'https://fishsounds.net/results-fish.js?query=Anguilla%20rostrata',
    'https://upload.wikimedia.org/wikipedia/commons/6/6d/Anguilla_rostrata.jpg'
  ),
  (
    'shortnose_sturgeon',
    'Shortnose sturgeon',
    'Acipenser brevirostrum',
    false,
    null,
    null,
    'Sound production is unconfirmed. soniferous is false so Atlantic sturgeon thunder is not attributed to shortnose sturgeon.',
    'Hudson resident. Spawning is earlier and farther upriver than Atlantic sturgeon.',
    'https://fishsounds.net/results-fish.js?query=Acipenser%20brevirostrum',
    'https://upload.wikimedia.org/wikipedia/commons/0/0d/Acipenser_brevirostrum.jpg'
  )
on conflict (id) do update set
  common_name = excluded.common_name,
  scientific_name = excluded.scientific_name,
  soniferous = excluded.soniferous,
  freq_low_hz = excluded.freq_low_hz,
  freq_high_hz = excluded.freq_high_hz,
  call_description = excluded.call_description,
  season = excluded.season,
  fishsounds_url = excluded.fishsounds_url,
  image_url = excluded.image_url;

insert into public.hydrophone_nodes (
  id,
  name,
  lat,
  lon,
  river_mile,
  hardware,
  sample_rate_hz,
  status,
  last_heartbeat
) values
  (
    'westpoint-cornwall',
    'West Point / Cornwall',
    41.4150,
    -73.9600,
    54.0,
    'Simulated SoundTrap-class hydrophone',
    48000,
    'simulated',
    now()
  ),
  (
    'poughkeepsie',
    'Poughkeepsie',
    41.7210,
    -73.9390,
    75.0,
    'Simulated SoundTrap-class hydrophone',
    48000,
    'simulated',
    now()
  ),
  (
    'tappan-zee',
    'Tappan Zee / Piermont',
    41.0630,
    -73.8900,
    26.0,
    'Simulated SoundTrap-class hydrophone',
    48000,
    'simulated',
    now()
  )
on conflict (id) do update set
  name = excluded.name,
  lat = excluded.lat,
  lon = excluded.lon,
  river_mile = excluded.river_mile,
  hardware = excluded.hardware,
  sample_rate_hz = excluded.sample_rate_hz,
  status = excluded.status,
  last_heartbeat = excluded.last_heartbeat;

-- Coordinate notes (not stored as columns):
-- westpoint-cornwall is an approximate mid-channel point in the West Point
-- to Cornwall reach near river mile 54. The USGS West Point gauge used
-- elsewhere in this repo is farther south at river mile 50 (41.386, -73.955).
-- poughkeepsie matches the HRECOS / USGS 01372043 station coordinate at
-- river mile 75.
-- tappan-zee sits in the Tappan Zee between the Piermont USGS gauge
-- (41.043, -73.896, river mile 25) and the Mario M. Cuomo Bridge (about
-- river mile 27), rather than on Piermont Pier.

-- Simulated imaging sonar at the focus site. Same id and coordinates as the
-- hydrophone so striped_bass_passage_and_calls_hourly can join on node id.
-- Poughkeepsie and Tappan Zee are later sonar sites and are not seeded.
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
