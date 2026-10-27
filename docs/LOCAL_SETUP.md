# ₹0 local setup and upload boundaries

## Local dependencies

- The project builder, manifest validation, Telugu subtitle generation, project
  output, approval hashes, OAuth HTTP flow, and YouTube API client use Python
  standard library modules.
- MP4 rendering requires FFmpeg and ffprobe in `PATH`; the subtitle filter and
  an installed Telugu-capable font (Windows default: Nirmala UI) are required.
- Offline generated Telugu narration uses the AI4Bharat Indic Parler-TTS
  checkpoint. Telugu is listed among its supported languages; its suggested
  Telugu speakers include Prakash and Lalitha. The model has about 0.9B
  parameters and its first inference downloads weights. Python packages are
  listed in `requirements-tts.txt`, but the TTS stack was not installed or
  executed in this repository. Check Python/PyTorch wheel compatibility and
  available RAM/VRAM before installing or downloading the model. CPU is the
  default and may be slow. A creator-recorded WAV can be used instead.
- Do not enable Google Cloud Billing. The YouTube Data API has free quota
  buckets, but uses a Google developer project and OAuth consent. The current
  official quota guide lists up to 100 `videos.insert` calls per day and
  10,000 units/day for other methods. Quota exhaustion stops uploads; do not
  attempt to bypass it.

## OAuth configuration (user performs locally)

1. Create/select a Google developer project and enable YouTube Data API v3;
   leave billing disabled.
2. Configure an OAuth consent screen and an installed/desktop OAuth client.
   In testing mode, add the owner account as an allowed test user if requested.
3. Save Google's client JSON outside tracked source (the repository ignores
   `client_secret*.json`). Never paste it or any token into chat.
4. Run the `authorize` command locally. The browser handles Google sign-in;
   this program never requests the account password. Refresh tokens are stored
   with Windows DPAPI in the user's local application-data folder.
5. Before an upload, display the channel, metadata, visibility, made-for-kids
   choice, synthetic-media declaration, and the YouTube Terms/copyright notice.
   Upload requires a separate exact typed approval phrase tied to the video and
   metadata hashes. The upload command checks that approval again before any
   YouTube API call.

YouTube documentation describes OAuth as the user-consent mechanism for
uploads. The standard quota is not a guarantee of project approval or account
eligibility. YouTube may require policy/app verification, and visibility rules
can depend on the API project. Verify the current Google Console and policy
state before relying on public upload; this code always sends an explicit
privacy value and does not infer public visibility.

## Rights and generated content

The built-in backgrounds are procedural geometric shapes created by this
project. Any added image, narration, or music must be owned by the creator or
licensed for the intended YouTube use. Music is optional. Keep a rights note
with the project. Decide YouTube's made-for-kids and synthetic-content
disclosures accurately for each upload; code does not guess these declarations.
