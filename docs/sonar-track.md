# Sonar track: counting fish that do not call

Hydrophones on this network hear Atlantic sturgeon thunder and, during the spawn, the surface splash of a striped bass "rock fight" (`bass_spawning_splash`). They do not count fish. Striped bass, Atlantic sturgeon, and river herring (alewife and blueback) are the counts this track is for, in that order. American shad does not make a species-specific swim-bladder call either, and it stays in the length model because adult shad overlap striped bass. Counting fish at a fixed site needs an imaging sonar or a split-beam echosounder aimed across the channel.

This document is the research note for that second track. The tables are `sonar_nodes` and `sonar_tracks`. The view `fish_passage_hourly` counts tracks, which is an individual-fish count. It is not `detection_counts_hourly`, which counts sound events. Nothing below is a field result from the Hudson. The simulator and the classifier in `edge/sonar` and `ml/sonar` run on synthetic tracks.

Focus site: West Point / Cornwall (`westpoint-cornwall`, about river mile 54). Poughkeepsie and Tappan Zee are later sites. Only West Point is seeded.

Priority for labels, for the Lowrance size class, and for any later classifier is striped bass, then Atlantic sturgeon, then river herring. American shad is not dropped from the synthetic model, because that overlap is how a length rule calls a bass wrong. It is not the species this project is trying to count first.

## What can count fish passing a fixed river site

Three families of instrument show up in river passage work. All of them fail in turbid water less often than a camera, which is why they are used on the Hudson at all. None of them identifies species the way a biologist with a fish in hand does.

### Imaging sonar (DIDSON, then ARIS)

Sound Metrics dual-frequency identification sonar (DIDSON) and its successor, the Adaptive Resolution Imaging Sonar (ARIS), form a multibeam acoustic image. A fixed unit looks across the river, like a counting tower that does not need clear water. Alaska Department of Fish and Game describes the operation directly: a technician counts fish in the playback, can stop and replay, and can mark direction because the image shows which way the body is moving. Length from the image has been used to separate large Chinook from smaller salmon. ADF&G also states the limit that matters here: no river sonar they use can separate species of similar size from the image alone. Their length method on the Kenai is for fish that differ in size, and they treat length as usable out to about 100 feet from the transducer.

- ADF&G, "Sonar Tools: DIDSON": https://www.adfg.alaska.gov/index.cfm?adfg=sonar.didson
- ARIS Explorer 1800 product page (identification mode 1.8 MHz, nominal range 15 m; detection mode 1.1 MHz, nominal range 35 m; 96 or 48 beams; 28° by 14° field of view): http://www.soundmetrics.com/products/aris-sonars/aris-explorer-1800
- ARIS Explorer 1800 specifications: http://www.soundmetrics.com/products/aris-sonars/ARIS-Explorer-1800/016622-A-ARIS-Explorer-1800-Specifications
- ARIS Explorer 3000, as sold for inspection, is the shorter-range higher-frequency unit (3.0 MHz out to about 5 m, 1.8 MHz out to about 15 m, 128 or 64 beams): https://mfe-is.com/offshore/aris-explorer-3000/

Sound Metrics does not publish a purchase price. Rental houses ask for a quote. This note does not invent a capital cost for an ARIS or a DIDSON.

A Hudson deployment would be a tripod or a pole on the bank, transducer aimed across the channel, recording continuously through the spring run. West Point is wide and deep relative to a 15–35 m acoustic window, so one unit does not see the whole cross-section. Counts are fish that passed through the beam, not a river-wide census, unless several units are installed and the unsampled fraction is estimated.

### How an ARIS or DIDSON count is produced

The raw product is a sequence of frames, not a species label.

1. **Detect.** Each frame is background-subtracted and smoothed. A target is a blob above a size and intensity threshold. Kang (2011) wrote the Echoview template most later river studies cite: noise subtraction, smoothing, detection, then conversion of each blob to a single target, on DIDSON data from the Rakaia River. Measured properties include length, thickness, perimeter, compactness, and orientation. https://doi.org/10.5657/fas.2011.0218
2. **Track.** Targets are linked across frames (Kang used an alpha-beta tracker). A track has a start, an end, a speed, and a change in position. Helminen and Linnansaari (2021) did this on 1.1 MHz ARIS Explorer 1800 data covering about 30 m of the Little Southwest Miramichi. Upstream counts matched human counts more closely than downstream counts. They filtered dynamic noise and milling fish, then used a model to decide whether a downstream object was a fish. https://doi.org/10.1016/j.fishres.2021.105883
3. **Direction.** Direction is the along-river component of the track. Upstream and downstream are the passage counts. Milling fish reverse or circle inside the beam; leaving them in the passage total double-counts one animal. The Hudson bass spawn is milling, so this track stores `milling` as its own direction rather than forcing every track into upstream or downstream.
4. **Length.** Length is the distance between the two ends of the body in the geometrically scaled image. Range and beam angle set the scale. The vertical beam is wide (about 14° on an Explorer 1800), so elevation inside the beam is unresolved and a tilted fish looks short. ADF&G's rule of thumb is above. A fish whose endpoints are hidden by another fish should be left unmeasured.
5. **One fish, one track.** The passage count is the number of accepted tracks, not the number of frames and not the number of pings. That is what `fish_passage_hourly.fish_count` stores.

Echoview's imaging-sonar workflow is the commercial version of the same steps (detect, filter on size and shape, track, read direction and speed): https://echoview.com/products-and-services/echoview/echoview-fish-counting/

### Split-beam echosounder (Simrad EK80 class, BioSonics)

A split-beam scientific echosounder does not draw a picture of the fish. It measures target strength and, from the phase difference across a split transducer, the angle of the target inside the beam. Consecutive single echoes become a three-dimensional track with range, speed, and direction. Length is not read off an image. It is inferred from target strength through an empirical regression that depends on species, swim bladder, frequency, and aspect. Those regressions overlap heavily for clupeids and for bass-sized fish, so target strength is a poor species id in a mixed estuary.

Instruments in this class include the Kongsberg Discovery Simrad EK80 and the BioSonics scientific echosounders used for fixed-station passage work. Product pages, without a public list price:

- Kongsberg EK80 family (split-beam transducers are a license and a transducer choice on the same wideband transceiver): https://www.kongsberg.com/what-we-do/ocean-space/ocean-science/ek-scientific-echo-sounder/
- BioSonics DT-X Extreme, which the vendor lists for fixed-location fish passage as well as mobile surveys: https://www.biosonicsinc.com/products/dt-x-extreme/

Alaska's river-counting program moved many sites from split-beam to DIDSON and ARIS precisely because the image resolves adjacent fish and gives a length and a direction the split-beam trace does not. Split-beam remains the right tool when the question is target strength or a deep, narrow beam rather than a picture.

### Cheaper forward-looking sonar (research only)

Consumer live sonars are multibeam imagers sold for fishing, not for a calibrated passage count.

- Garmin announced LiveScope Plus in 2022 at a suggested retail price of $1,699.99 for the GLS 10 black box plus LVS34 transducer, and $1,199.99 for the transducer alone. That is the 2022 suggested retail price, not a current quote. https://www.garmin.com/en-US/newsroom/press-release/marine/garmin-unveils-livescope-plus-with-enhanced-resolution-clearer-images-and-even-better-target-separation/
- Lowrance lists ActiveTarget 2 (module, transducer, and mounts) at $1,399.99 and the transducer alone at $999.99 on the product pages retrieved for this note. https://www.lowrance.com/products/transducers/activetarget-2/active-target-2/ and https://www.lowrance.com/products/transducers/activetarget-2/active-target-2-transducer-only/

These units can show fish and a heading in real time. They are not a substitute for an ARIS on a counting station until someone has checked length against known fish, documented the range at which adjacent fish merge, and shown that an unattended mount holds its aim. The Hudson at West Point is deeper, more turbid, and wider than the pond or the reservoir these products are demonstrated in. Treat them as a cheap experiment, and keep the data model the same so a later ARIS can write the same `sonar_tracks` rows.

The boat unit available now is not one of those forward-looking sonars. It is a Lowrance with Primary and Secondary CHIRP (conventional 2D), DownScan, and SideScan. It does not have ActiveTarget or any other live forward beam. A log from that unit is a down-looking and side-looking record. The importer below reads it. It does not turn it into a cross-channel passage count.

Florida International University publishes internal daily recharge rates for a DIDSON and for Simrad EK80 wideband transceivers (on the order of tens to about $160 per day, internal users). Those are university bench rates, not the cost of buying or fielding a system. https://research.fiu.edu/facilities-and-administrative-costs/facilities/recharge/fiu-marine-acoustics-recharge-center/

## Species classification from sonar

Published approaches, in the order a Hudson station would actually try them:

**Length distributions.** Gurney et al. (2014) assigned species and age to salmonid DIDSON lengths with a mixture model, and showed how badly a hard length cutoff fails when the distributions overlap. https://doi.org/10.1080/00028487.2013.862185 ADF&G uses the same idea only where king salmon are clearly longer than the other salmon in the image. On the Hudson the overlaps are the whole problem: large striped bass, small Atlantic sturgeon, and adult shortnose sturgeon share tens of centimetres. See Limits.

**Swimming behavior.** Helminen and Linnansaari (2021) measured tailbeat frequency from ARIS Explorer 1800 frames of Atlantic salmon, striped bass, and American shad in a shallow experimental pond (0.8 m deep, slow flow). Manual counts differed by species (mean ± 1 SD beats/s: salmon 0.6 ± 0.3, striped bass 0.9 ± 0.2, shad 1.4 ± 0.3). An automated peak counter did not match the manual counts well, especially for striped bass (mean bias 4.8 beats on a track) and especially when fish were dense. In that same short-range setup the mean sonar length minus fork length was −4.1 cm for salmon, −0.6 cm for striped bass, and +5.1 cm for shad. Those are pond numbers, not a Hudson error budget. https://doi.org/10.1002/tafs.10318 The pond dataset is one of the few public files that actually contains striped bass and American shad. It is not a river deployment. https://doi.org/10.6084/m9.figshare.14423630

Direction and milling are also behavior. Helminen and Linnansaari (2021), cited above, had to remove milling tracks before a passage count was usable. A surface cluster of bass on the Hudson is milling on purpose.

**Deep learning on ARIS or DIDSON frames.** Zang et al., Remote Sensing 2021, 13(14), 2671, trained a convolutional net to separate American eel from other objects in imaging-sonar frames. Laboratory image accuracy was above 98 percent. On field data at the Iroquois Dam (St. Lawrence River) they report accuracy in line with human experts. That is an eel-versus-not task, not a four-species Hudson task. https://www.mdpi.com/2072-4292/13/14/2671 and https://doi.org/10.3390/rs13142671

Fernandez Garcia, Martignac, and colleagues released a YOLO-format training set of ARIS and DIDSON frames from the Touques and Sélune rivers (Normandy), with Atlantic salmon, European eel, sea lamprey, allis shad, European catfish, unidentified fish, and empty frames, plus about 40 hours of validation video annotated for passages longer than 20 cm. Allis shad is not American shad. Nothing in that set is a Hudson species except by family resemblance. https://doi.org/10.5281/zenodo.5046707 and https://doi.org/10.5281/zenodo.5092009

Caltech Fish Counting 2026 (CFC26) is a public ARIS benchmark for detection, tracking, and counting, not for species. The dataset card lists 4,363 clips, on the order of a million boxes, and 14,072 tracks from eleven sites on nine Pacific salmon rivers, with temporal train/validation/test splits. The paper (Stathatos et al.) is https://huggingface.co/papers/2610.22549 and the data is https://huggingface.co/datasets/perona-lab/cfc26 (CC BY 4.0). A small positive-frame sample is https://huggingface.co/datasets/perona-lab/cfc26-mini. CFC26 is the right place to test a future detector and tracker. It does not label striped bass, river herring, American shad, or Atlantic sturgeon.

The code in `ml/sonar` does not train on any of these files. It trains on tracks drawn from `sonar_node.simulate`. Those metrics are synthetic. See that README before quoting a number.

## Seasonal timing on the Hudson

West Point sits in the historical striped bass spawning reach and downstream of the main American shad and Atlantic sturgeon spawning reaches. A sonar there sees a mix of local spawning and fish on their way through.

**Striped bass.** First priority. Adults return in spring. The 1974–1975 egg surveys summarized for the Hudson found spawning from early May through June, with the peak in mid-May, concentrated between Croton–Haverstraw and West Point (about river mile 34–55). https://nepis.epa.gov/Exe/ZyPURL.cgi?Dockey=9100HG0E.TXT NYSDEC still samples the spawning stock with a haul seine and electrofishing from April through June. https://dec.ny.gov/nature/animals-fish-plants/hudson-delaware-marine-fisheries/striped-bass A NYSDEC access guide gives the angling run as March through June and a size range of about 18 to 55 inches (roughly 46 to 140 cm) and 3 to 70 pounds. https://extapps.dec.ny.gov/docs/remediation_hudson_pdf/hrefba.pdf The current Hudson slot limit is 23–28 inches total length, chosen because most fish over 28 inches in the river are female. That slot is a regulation, not a length distribution.

Spawning behavior is a group at the surface. The U.S. Fish and Wildlife Service species profile, quoting Setzler et al. (1980), describes one female surrounded by up to 50 males, at or near the surface. https://www.govinfo.gov/content/pkg/GOVPUB-I49-PURL-LPS73961/pdf/GOVPUB-I49-PURL-LPS73961.pdf Anglers call the resulting splash a rock fight. https://liboatingworld.com/a-striper-the-prized-catch/ The hydrophone contract name for that splash is `bass_spawning_splash`, with `species_id = striped_bass`. It is a surface noise, not a swim-bladder call, and one splash is not one fish. The simulator's spawning bass are shallow, clustered, and mostly `milling` for that reason.

**Atlantic sturgeon.** Second priority. NYSDEC: adults return to spawn in May and June, are sampled with gill nets from mid-May through June near Hyde Park, and can grow to 14 feet and 800 pounds. Juveniles stay in the river two to six years. Shortnose sturgeon are generally under 4 feet and under 20 pounds, and spawn nearer Albany in May. https://dec.ny.gov/nature/animals-fish-plants/hudson-delaware-marine-fisheries/atlantic-and-shortnose-sturgeon Hyde Park is upriver of Poughkeepsie. West Point sees migrants, not the spawning aggregation. Cohen et al. (2025) recorded sturgeon thunder at Hyde Park in June and July 2021; that is the acoustic season already stored on `species`, and it sits slightly later than the gill-net window. The simulator draws adult passage fish from 100–250 cm between May and mid-July. It does not draw the 14-foot animals, and it does not draw the juveniles that overlap bass lengths. Both omissions are stated so a perfect score on synthetic data is not read as a field result.

**River herring.** Third priority. Alewife and blueback herring are one species row (`river_herring`) because a sonar length will not separate them. NYSDEC's sustainable fishery plan: alewives enter as early as mid-March and spawn through mid-May; blueback herring generally arrive in April and spawn into early June. Adults spawn in tributaries and in the shallow main stem. The commercial season in the river is 15 March through 15 June. The plan says mean length and mean length-at-age have increased since consistent sampling began in 2012, and does not publish a single adult length this simulator should copy. https://extapps.dec.ny.gov/docs/fish_marine_pdf/nyherrsfmp.pdf and https://dec.ny.gov/nature/animals-fish-plants/hudson-delaware-marine-fisheries/river-herring The simulator draws 20–35 cm as an adult envelope. That is a model bound, not a measured Hudson mean.

**American shad.** Not a priority count. NYSDEC samples the spawning stock from April through June. https://dec.ny.gov/nature/animals-fish-plants/hudson-delaware-marine-fisheries/american-shad The recovery plan places spawning in freshwater from Kingston (river km 145) to Troy (river km 244), with haul-seine sampling from April through the first week of June between river km 88 and 224. https://extapps.dec.ny.gov/docs/fish_marine_pdf/hudsonshadplan.pdf West Point (river mile 54, about river km 87) is at the downstream edge of that sampling reach, so most shad at this site are passing, not spawning on the Kingston–Troy flats. The same NYSDEC access guide says adults average 20–23 inches (about 51–58 cm) and 5–6 pounds. The Conservationist (April/May 2023) describes the run as typically late March through early June. https://extapps.dec.ny.gov/docs/administration_pdf/0423consmag.pdf The simulator draws 40–60 cm, which covers that average and cuts both tails. That band sits inside the striped bass envelope, which is why the rules classifier's shad-to-bass mistakes are the result worth keeping.

## Limits

- **Size overlap.** Adult river herring (simulator 20–35 cm) overlap small striped bass. Adult shad (about 51–58 cm in the NYSDEC access guide) overlap male and small female bass. Bass over about 100 cm overlap the small end of the adult Atlantic sturgeon draw and the large end of shortnose sturgeon (generally under 4 feet, about 122 cm). White perch and other Morone are not even in the four-class model. Length plus a school-versus-surface rule will not resolve those cases. Gurney et al. (2014) is the cautionary paper.
- **Ground truth.** A track gets a species only after something else identifies the fish: a net, a weir, a known-length release, or a human review of the clip. `review_status` stays `unreviewed` until that happens. Rejected tracks drop out of `fish_passage_hourly`. Tracks with a null `species_id` drop out too, so the view is not "every target the sonar saw."
- **Beam coverage.** One ARIS does not cover the West Point cross-section. Fish above, below, or inshore of the beam are invisible. Dense schools merge into one blob.
- **Length bias.** Tilt, overlap, and unresolved elevation shorten or stretch the image. The simulator's length noise (normal, 5 cm standard deviation, applied to the length the classifier sees) is a placeholder, not a measured error budget.
- **Tailbeat is not in the synthetic tracks.** The Helminen pond result is real and is not reproduced here. No synthetic tailbeat frequency is stored, because inventing one would look like a measurement.
- **Splash detections are not fish counts.** `bass_spawning_splash` is a hydrophone event. Many males can make one noisy minute, and a silent cluster makes none.

## NYSDEC acoustic telemetry is a different measurement

The Hudson River Fisheries Unit maintains a receiver array on Coast Guard buoys from New York Harbor to the Federal Dam at Troy. A tagged fish is logged as tag id, time, and receiver. It is an E-ZPass for that animal, not a count of untagged fish. The array has been in place, with Delaware State University, since 2009; a 2024 note describes 68 receivers and winter units that stay out under ice. Coastwide detections are shared beyond the Hudson.

- Program page, including the current multispecies study (blueback herring, Atlantic and shortnose sturgeon, American eel, striped bass, grass carp): https://dec.ny.gov/nature/animals-fish-plants/hudson-delaware-marine-fisheries
- Array description (68 receivers, Harbor to Troy): https://content.govdelivery.com/accounts/NYSDEC/bulletins/3c56e86
- Shortnose population work that paired telemetry with side-scan sonar, which images fish on the bottom rather than counting passage through a horizontal multibeam: https://dec.ny.gov/news/press-releases/2025/6/back-from-the-brink-dec-announces-new-collaborative-study-estimates-population-of-hudson-river-endangered-shortnose-sturgeon

A tagged striped bass that passes West Point can be joined to sonar tracks from the same hour only as a presence check. The tag does not tell you which track was that fish, and most fish in the beam have no tag. Side-scan counts of sturgeon on the bottom answer a different question again (how many animals are resting in an area) and should not be written into `sonar_tracks` without their own method flag. This schema does not store telemetry hits.

## Fusing sonar tracks with hydrophone detections

Same site id on both tables. `sonar_nodes.id` for the seeded unit is `westpoint-cornwall`, the same text id as `hydrophone_nodes`. There is no foreign key between them: a sonar can exist without a hydrophone. The join is on that shared id plus the UTC hour.

`striped_bass_passage_and_calls_hourly` full-outer-joins striped bass rows of `fish_passage_hourly` to `detection_counts_hourly`. Hydrophone columns on that view:

- `splash_detections` is the hour's `bass_spawning_splash` events
- `striped_bass_detections` is every non-rejected detection that hour with `species_id = striped_bass`, splash included when the hydrophone row is labeled that way

Both hydrophone numbers are hour totals. They repeat on every sonar `direction` row for that hour. Summing them across directions counts the same splashes twice. Sonar `fish_count` is per direction and may be summed across directions. A hydrophone-only hour has a null `direction` and a null `fish_count`.

The hydrophone node does not have to emit `bass_spawning_splash` for this view to exist. Until it does, `splash_detections` stays zero and the view is only the sonar side.

## Recording a Lowrance log

This is the procedure for the unit on the boat: Primary and Secondary CHIRP, DownScan, and SideScan. There is no ActiveTarget transducer, so there is no forward live image to turn on and nothing in these files is a horizontal multibeam across the river.

1. Put a microSD card in the unit. Lowrance's own logging notes say the card, not internal memory: a sonar log fills the internal store quickly. On HDS Pro the control is Log sonar, from System Controls or from Sonar settings, and Save to should be the card. On earlier HDS units it is Log Sonar Data on the Sonar menu, and Save to is the card. Stop logging before you pull the card. A red flashing marker means a log is still open.
2. Record every channel the unit is pinging. On earlier HDS software that checkbox is Log all channels: broadband (Primary and Secondary) plus StructureScan DownScan and SideScan, written as `.sl2` rather than a sonar-only `.slg`. On current HDS software pick `.sl2` (sonar and structure) or `.sl3` (the same family, and StructureScan 3D if the unit has it). Do not pick `.slg` if you want DownScan and SideScan in the file. `.xtf` is for other software and this importer does not read it.
3. Use a higher bytes-per-sounding setting when the card has room. The manual tradeoff is resolution against file size. A short anchored session is small even at the higher setting.
4. Anchor or drift in a spot where you already see striped bass. Note the time and the spot in ordinary language (bank, buoy, river mile). The log's GPS is what the importer uses. A session of ten or twenty minutes is enough for a first file. Keep the transducer in the water and the 2D, DownScan, and SideScan pages alive so those channels are actually pinging. SideScan from an anchored boat is a short swath beside the hull, not a survey of the reach.
5. Copy the `.sl2` or `.sl3` off the card and run the importer from `edge/sonar` (the package lives on `src`; `pip install -e .` or `PYTHONPATH=src`):

```bash
python -m sonar.import_lowrance file.sl2 --node westpoint-cornwall --dry-run
```

`--dry-run` writes `out/sonar_tracks.jsonl` and does not open the network. `--node` pins the row to a sonar site. If you leave it off, the importer picks the nearest station in `data/stations.json` and then the sonar site nearest that station (`west_point` becomes `westpoint-cornwall`). A fix more than 30 km from every station is refused until you pass `--node`, so a log from somewhere else is not glued to Piermont.

What the file can and cannot say:

- A stationary down-looking beam counts fish that pass through the cone under the boat. That number is an index of fish under the boat. It is not a count of the river, not a cross-section, and not `fish_passage_hourly`.
- Direction is stored as `unknown`. Primary/Secondary arches and DownScan/SideScan marks do not show upstream versus downstream.
- `species_id` stays null. `species_confidence` stays null. No species model ran. A mark whose rough length sits in 30–120 cm is `features.bass_candidate = true` and `size_class = striped_bass_candidate`, including lengths that also fit river herring (about 30–35 cm), American shad (about 40–60 cm), or a small sturgeon (about 100–120 cm). Those overlaps are written in `overlap_notes`. A longer mark can be `sturgeon_sized`. A shorter adult-herring mark can be `herring_sized`. None of those labels is an identification.
- Length is not fork length. If the boat is moving at least 0.4 m/s, `length_cm` is GPS speed times how long the mark stayed bright, which includes the footprint of the beam. If the boat is anchored or drifting slower than that, `length_cm` is the height of the bright pixels in the water column. `peak_intensity` is the raw 0–255 sample, not target strength in dB.
- The same fish on Primary and on DownScan can become two rows. This importer does not match across channels.
- Surface clutter and the bottom return are rejected inside the detector. That rejection has been checked on synthetic logs, not on a Hudson log against known fish. Do not quote a detection rate from this code.

Rows are `source = lowrance_log`. They stay out of `fish_passage_hourly` until something sets `species_id`. Upload, when you are ready, is the same command without `--dry-run` and with `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` set. The node must already exist; only `westpoint-cornwall` is seeded.

Lowrance manuals for the menu names: HDS-5/7 operator manual 988-10041-001 (Log Sonar Data, Log All Channels, Save to the card) and the HDS Gen2 Touch sonar page (Log all channels writes `.sl2`). Current HDS units name the same control Log sonar and offer `.sl2` and `.sl3` as the formats that include structure channels.

- https://cxjdfr.files.cmp.optimizely.com/download/assets/en-us-HDS-5-7-5M-7M_OM_EN_988-10041-001_w.pdf/b5d7a324045a11f09811bad2b99c6e07
- https://www.manualshelf.com/manual/lowrance/hds-9-gen2-touch/operation-manual-english/page-48.html

The frame layout follows the MIT readers python-sllib (https://github.com/opensounder/python-sllib) and sonarlight (https://github.com/KennethTM/sonarlight). The SL2 water-depth float and the SL3 flags and millisecond fields are the sllib offsets; those match sonarlight's public example files, and sonarlight's published SL2 water-depth offset does not. The parser is in `edge/sonar` and is not a copy of either package.

## What the software in this repo actually does

`edge/sonar` draws synthetic tracks with the length envelopes and the seasonal windows above. The hourly rate is a count of groups (a school, a surface cluster, or one solitary fish), not a population estimate. About one in eight schooling or spawning fish is drawn alone, so a single mid-size target stays ambiguous. The baseline classifier is length and behavior rules. It can upload with the service role. `ml/sonar` fits a linear classifier on those tracks and leaves a stub for a future model that reads ARIS frames. The metrics in that directory are from this generator.

`python -m sonar.import_lowrance` reads a real Lowrance `.sl2` or `.sl3` and writes `sonar_tracks` with `source = lowrance_log`. No Hudson log has been scored against known fish. The synthetic metrics are not a detection rate for that importer.
