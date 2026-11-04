/**
 * Fish Sounds — Supabase connection for the GitHub Pages site.
 *
 * The anon key is meant to be public. It can only do what Row Level Security
 * allows. For this tab that is read-only access to species, hydrophone_nodes,
 * detections, and the detection_counts_hourly view, plus playback of clips in
 * the public "audio" storage bucket. Never put the service-role key here.
 *
 * Where to set the values:
 *   1. Open this file (config.js, next to index.html).
 *   2. In Supabase: Project Settings → API.
 *   3. Paste the Project URL into supabaseUrl.
 *   4. Paste the anon public key into supabaseAnonKey.
 *   5. Commit and push to main (GitHub Pages redeploys from .github/workflows/pages.yml).
 *
 * Leave both strings empty to use the bundled sample feed in
 * data/fish-sounds.json. The Fish Sounds tab still loads: map, hourly
 * activity, species cards, and in-browser sample clips.
 */
window.HRECOS_CONFIG = {
  supabaseUrl: "",
  supabaseAnonKey: ""
};
