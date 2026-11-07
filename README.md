# Hey Muse ESP32-S3 — Custom Animated Robot Avatar

An unofficial, community-maintained fork of the [Muse Gadgets SDK](https://github.com/facebookincubator/muse-gadget-sdk), adding a custom pixel-art robot avatar and on-device **“Hey Muse”** wake-word detection to supported ESP32 devices.

> **Tested custom-avatar hardware:** Waveshare **ESP32-S3-Touch-AMOLED-1.75-B** (the non-C 1.75-inch board). For this board, use the **`s3n`** build target. **Do not use `s3`**, which selects the distinct 1.75C hardware profile.
>
> **Release source:** The custom-avatar work is on the [`feature/smooth-animation`](https://github.com/guyverckw/Hey-Muse-esp32-s3/tree/feature/smooth-animation) branch. A quick start that checks out this branch is provided below. The default branch may not contain the same avatar features.

## What works

- Custom 64×64 RGB565 robot sprite avatar with animated **Idle, Blink, Listening, Thinking, Speaking, Happy, Boot, Error, Power-off and Sleep/Wake** states.
- More fluid multi-frame Idle, Listening and Thinking animation, plus audio-responsive Speaking animation.
- Local **“Hey Muse”** wake-word recognition; conversation processing uses the Muse connection.
- Touchscreen UI and Muse mobile-app pairing over Bluetooth with Wi-Fi setup.
- Optional spoken replies using **Fish Audio**; the API key is supplied by each user.
- **Multilingual voice conversations verified on hardware:** English, Cantonese (廣東話), and Mandarin (普通話). The author tested speaking and receiving spoken replies in all three languages using the existing Muse/Fish Audio voice pipeline; **no firmware changes were needed**. Broader language coverage and seamless automatic switching have not been verified. See the [multilingual test notes](docs/MULTILINGUAL.md).

This is a personal/community project, not made or endorsed by Meta. Features and external services can change. The custom-avatar configuration has been tested on a 1.75-B; other supported hardware profiles may need separate testing.

## Quick start — Waveshare 1.75-B

**Prerequisites:** macOS or Linux, Git, a USB **data** cable, [ESP-IDF v6.0.1](https://docs.espressif.com/projects/esp-idf/en/release-v6.0/esp32s3/get-started/index.html) with ESP32-S3 support, your own [Muse SDK token](https://gadgets.muse.ai/settings/sdk-tokens), the Muse mobile app, and access to a trusted **2.4 GHz Wi-Fi** network. For spoken replies, obtain an optional [Fish Audio API key](https://fish.audio/app/api-keys).

```bash
# 1. Clone the correct branch
git clone --branch feature/smooth-animation --single-branch \
  https://github.com/guyverckw/Hey-Muse-esp32-s3.git
cd Hey-Muse-esp32-s3/esp32

# 2. Activate your installed ESP-IDF 6.0.1 environment
. ~/esp/esp-idf-v6/export.sh

# 3. Configure your PERSONAL Muse SDK token for the 1.75-B build
B=build-muse-waveshare-s3-175
idf.py -B "$B" -DIDF_TARGET=esp32s3 \
  -DSDKCONFIG="$B/sdkconfig" \
  -DSDKCONFIG_DEFAULTS="sdkconfig.defaults;devices/sdkconfig.muse;devices/sdkconfig.muse-waveshare-s3-175" \
  menuconfig
# In menuconfig, search for GADGET_SDK_TOKEN; save and exit.

# 4. Compile the 1.75-B image (may take a while)
tools/muse/board.sh build s3n

# 5. Identify the connected serial port, then flash
# macOS: ls /dev/cu.usbmodem*
# Linux: ls /dev/ttyACM* /dev/ttyUSB* 2>/dev/null
tools/muse/board.sh flash s3n YOUR_SERIAL_PORT
```

Replace `YOUR_SERIAL_PORT` with the actual port, e.g. `/dev/cu.usbmodem14201` on macOS or `/dev/ttyACM0` on Linux. **Do not type the example port unless it is actually yours.** Do not run `erase-flash`: normal flashing should preserve existing pairing, Wi-Fi and Fish Audio settings on an already-configured device.

**New to ESP-IDF, setting up Muse, or enabling Fish Audio?** Follow the full **[1.75-B setup and troubleshooting guide](docs/QUICKSTART_175B.md)**. It explains every step, including ESP-IDF installation, first-time pairing and how to save a Fish Audio API key.

## Board profiles: choose carefully

| Hardware | Helper target | Build directory | Guidance |
| --- | --- | --- | --- |
| **Waveshare ESP32-S3-Touch-AMOLED-1.75-B / non-C 1.75** | **`s3n`** | `esp32/build-muse-waveshare-s3-175/` | **Tested custom avatar: [quick start](docs/QUICKSTART_175B.md)** |
| Waveshare ESP32-S3-Touch-AMOLED-1.75C | `s3` | `esp32/build-muse-waveshare-s3-175c/` | [Existing 1.75C setup guide](docs/SETUP.md); custom-avatar experience not verified here |

**The two board targets are not interchangeable.** Check the exact name printed on the board or its product documentation before flashing.

## Device pairing and voice replies

After the first flash, open the Muse app, enable developer mode under **Settings → Devices**, add the nearby `MuseGadget-XXXXXX` device, and follow the on-screen prompts to set up Wi-Fi and pairing. To add Fish Audio spoken replies, return to `esp32/` with the board connected over USB, close any serial monitor, and run:

```bash
python tools/muse/save_fish_api_key.py
```

The helper prompts for your key without echoing it and stores it in device NVS. On the board, check **Settings → Voice Replies**. The Fish Audio key is optional; without it, responses can still appear as text. Fish Audio is a network service, **not offline TTS**.

## Build maintenance and troubleshooting

- **Build log:** `tools/muse/board.sh build s3n` uses `/tmp/muse_build_s3n.log`. Check it with `tail -n 40 /tmp/muse_build_s3n.log`.
- **Compiler environment:** Activate the same ESP-IDF 6.0.1 and Python environment each time. If `idf.py` is unavailable, re-run the `export.sh` command.
- **Serial port:** Use a data-capable cable. List ports, and close other serial monitors before flashing.
- **SDK token:** A missing or invalid personal token may prevent pairing. Configure it locally in the **non-C** build configuration and rebuild.
- **Firmware size:** Verify that `esp32/build-muse-waveshare-s3-175/muse-gadget.bin` fits the app partition; **do not change partition layouts casually**.
- **Sprite source:** The robot PNGs and converter are under `esp32/avatar/assets/robot/`. The generated `robot_sprites.h` is checked in; **regeneration is not required for a normal clone/build**. To change artwork, see the [developer section](docs/QUICKSTART_175B.md#developers-customising-the-avatar).

## Security and responsible sharing

- **Every builder must supply their own Muse SDK token.** Keep your `sdkconfig` and any firmware binaries built with embedded credentials private.
- Keep Fish Audio keys, Wi-Fi passwords, device logs containing secrets, and credentials **out of Git and issue reports**. The current NVS configuration does not encrypt Fish Audio credentials at rest.
- Do not commit experimental backups, temporary installers, or credentials accidentally created as filenames. Check `git diff --cached --name-only` before every push.
- Review Muse and Fish Audio terms and applicable costs before use.

## Credits and licensing

This fork builds on the [Muse Gadgets SDK](https://github.com/facebookincubator/muse-gadget-sdk) and [wobsoriano/hey-muse](https://github.com/wobsoriano/hey-muse). See the repository [`LICENSE`](LICENSE) (Apache-2.0) and [`esp32/components/muse/models/HEY-MUSE-LICENSE`](esp32/components/muse/models/HEY-MUSE-LICENSE) (wake-model attribution). The custom avatar is a community modification.
