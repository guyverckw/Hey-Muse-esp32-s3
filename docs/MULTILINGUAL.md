# Multilingual voice conversations — tested capabilities

This page documents the voice-language capabilities tested by the maintainer on the **Waveshare ESP32-S3-Touch-AMOLED-1.75-B** running the custom-animated-avatar firmware (v9 source checkpoint `a65e22b`, `feature/smooth-animation`).

## Supported in the maintainer's hardware tests

| Language | Voice input understood | Spoken reply | Result |
| --- | --- | --- | --- |
| English | Yes | Yes | Passed |
| Cantonese (廣東話) | Yes | Yes | Passed |
| Mandarin Chinese (普通話) | Yes | Yes | Passed |

These were **manual end-to-end tests** with the existing Muse connection and Fish Audio TTS configuration. No firmware changes, speech-model replacement or extra font modification was required for these results.

## How to try it

Complete the normal [1.75-B installation and pairing guide](QUICKSTART_175B.md) first. Configure working Fish Audio spoken replies and ensure your device is online. Say the existing **“Hey Muse”** wake phrase, followed by one of these sample requests in the appropriate spoken language:

- **English:** “Hey Muse, please introduce yourself in English.”
- **Cantonese:** “Hey Muse，請用廣東話介紹一下自己。”
- **Mandarin:** “Hey Muse，请用普通话介绍一下自己。”

Check that the device understood the request and produced an intelligible spoken reply in the requested language. The avatar should continue its existing Listening, Thinking and Speaking animations.

## What this does not claim

- **Automatic language switching** across multiple turns has not yet been verified.
- **Mixed-language requests**, longer conversations, and pronunciation across different Fish Audio voices have not yet been systematically tested.
- Only **English, Cantonese and Mandarin** were confirmed. Other languages may work but are not validated by these tests.
- Language recognition and response generation depend on the connected Muse service; spoken replies depend on Fish Audio account, voice selection, connectivity and service availability. The assistant is **not fully offline**.
- The original local wake phrase remains **“Hey Muse”**. Local Cantonese or Mandarin wake-word detection was not tested.
- The CJK font is intentionally retained for future localisation; these voice tests do not guarantee every written character renders correctly on-screen.

## Developer note

Because all three tested languages already work with the current service pipeline, no multilingual firmware patch is needed for this milestone. Preserve the working firmware, models, fonts and sprite graphics. Record any future language tests here with their device, voice setup and results.
