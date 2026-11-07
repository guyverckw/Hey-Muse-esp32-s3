# Quick installation guide — Hey Muse custom avatar on Waveshare ESP32-S3-Touch-AMOLED-1.75-B

This guide covers a **fresh build from this fork's `feature/smooth-animation` branch**, including installation of ESP-IDF, firmware build and flash, Muse pairing, optional Fish Audio speech, and common troubleshooting.

> **Hardware warning:** This guide is for the **1.75-B / non-C** Waveshare board used to test the custom animated robot. Use **`s3n`**, not `s3`. The `s3` target selects the separate **1.75C** profile. For 1.75C instructions, see [`SETUP.md`](SETUP.md), and note that this fork's avatar has not been hardware-tested on that board.

## 1. Checklist

- Waveshare **ESP32-S3-Touch-AMOLED-1.75-B** board and a USB **data** cable.
- macOS or Linux computer, terminal, Git, Internet connection, and enough disk space for ESP-IDF toolchains and a full C/C++ build.
- **ESP-IDF 6.0.1** installed for `esp32s3`, using a compatible Python environment. The author's successful macOS environment used Python 3.10.6; always use the Python environment ESP-IDF installs and activates, rather than forcing one from another project.
- **Your own** [Muse SDK token](https://gadgets.muse.ai/settings/sdk-tokens) and Muse app with access to developer/community devices; review the [Muse SDK terms](https://gadgets.muse.ai/sdk-terms).
- A trusted **2.4 GHz Wi-Fi** network for initial pairing.
- Optional: your own [Fish Audio API key](https://fish.audio/app/api-keys) for spoken replies.

Do not post API keys, Wi-Fi passwords, SDK tokens, build `sdkconfig` files, or personal-token firmware binaries publicly.

## 2. Get the source from this fork

Open Terminal in a directory where you want to keep the source:

```bash
git clone --branch feature/smooth-animation --single-branch \
  https://github.com/guyverckw/Hey-Muse-esp32-s3.git
cd Hey-Muse-esp32-s3

git branch --show-current          # feature/smooth-animation
git rev-parse --show-toplevel      # the repository root
cd esp32
```

**Do not clone an older fork or use the default branch accidentally.** The tested animated robot is on the `feature/smooth-animation` branch. The author's stable v9 custom-avatar commit is `a65e22b` (use `git checkout a65e22b` if you intentionally want that exact snapshot).

## 3. Install ESP-IDF 6.0.1 (first time only)

Follow Espressif's [ESP32-S3 getting-started instructions](https://docs.espressif.com/projects/esp-idf/en/release-v6.0/esp32s3/get-started/index.html) for host prerequisites. On macOS, this generally includes Xcode command-line tools and the package dependencies described by Espressif. On Linux, install your distribution's corresponding host tools.

If ESP-IDF is not already installed, the following installs the supported tag (run from a **new terminal**):

```bash
mkdir -p ~/esp
cd ~/esp
git clone --branch v6.0.1 --recursive \
  https://github.com/espressif/esp-idf.git esp-idf-v6
cd esp-idf-v6
./install.sh esp32s3
. ./export.sh
idf.py --version
```

The `idf.py` version should identify **v6.0.1**. Every new terminal session must activate ESP-IDF again:

```bash
. ~/esp/esp-idf-v6/export.sh
```

If you installed ESP-IDF elsewhere, use the `export.sh` from **your installation**. The build directory remembers the Python environment; avoid mixing ESP-IDF versions or Python virtual environments.

Return to this fork's `esp32/` directory before running any project commands:

```bash
cd ~/Hey-Muse-esp32-s3/esp32
```

**If you cloned into a different parent directory**, replace that example path with your actual clone location. `pwd` and `git rev-parse --show-toplevel` can help locate it.

## 4. Configure your own Muse SDK token

The custom avatar's confirmed board profile is `waveshare-s3-175`. From the repository's **`esp32/` directory**, with ESP-IDF active:

```bash
B=build-muse-waveshare-s3-175
idf.py -B "$B" -DIDF_TARGET=esp32s3 \
  -DSDKCONFIG="$B/sdkconfig" \
  -DSDKCONFIG_DEFAULTS="sdkconfig.defaults;devices/sdkconfig.muse;devices/sdkconfig.muse-waveshare-s3-175" \
  menuconfig
```

1. In the configuration menu, use search (`/`) for **`GADGET_SDK_TOKEN`** (or find **Gadget SDK token**).
2. Enter your **own** token from the Muse developer portal.
3. Save and exit the menu.
4. The token stays in the **local board build configuration** (`build-muse-waveshare-s3-175/sdkconfig`). It is embedded in the resulting firmware; **do not upload the binary or this configuration file publicly**.

Do not paste a token as a standalone Terminal command: it may create a local filename containing the secret. If a token has been exposed, rotate/revoke it at the provider.

## 5. Build firmware for the correct board

From `esp32/`:

```bash
tools/muse/board.sh build s3n
```

The helper selects `esp32s3`, the **non-C** `waveshare-s3-175` configuration, and output directory `build-muse-waveshare-s3-175`. It prints a short summary and stores the full build log here:

```bash
tail -n 40 /tmp/muse_build_s3n.log
```

Verify that the command exited successfully and the file exists:

```bash
ls -lh build-muse-waveshare-s3-175/muse-gadget.bin
```

If a build fails, inspect the **first actual compiler error** in the log; don't start by erasing NVS or changing the partition table. Rebuilding from a clean clone is safer than applying installers intended for older development snapshots.

### Board command reference

| Board | Build | Flash |
| --- | --- | --- |
| **1.75-B / non-C (this guide)** | `tools/muse/board.sh build s3n` | `tools/muse/board.sh flash s3n PORT` |
| 1.75C (different hardware) | `tools/muse/board.sh build s3` | `tools/muse/board.sh flash s3 PORT` |

## 6. Flash without resetting pairing

Connect the board with a USB data cable, then identify its port. Example commands:

```bash
# macOS
ls /dev/cu.usbmodem*

# Linux (one or both patterns may exist)
ls /dev/ttyACM* /dev/ttyUSB* 2>/dev/null
```

Close serial monitors or other programs using that port. **Substitute the port shown on your computer**:

```bash
# Example only: replace the port!
tools/muse/board.sh flash s3n /dev/cu.usbmodem14201
```

On Linux, an example is `tools/muse/board.sh flash s3n /dev/ttyACM0`. Typical successful output includes a flash verification and hardware reset. The normal board helper flashes firmware and related images **without performing a whole-chip erase**. Existing NVS settings normally survive; do not use `erase-flash` or reset pairing as a routine step.

## 7. Pair with Muse and Wi-Fi (first-time install)

1. Install/open the Muse app on your phone and sign in.
2. Enable developer/community device access under **Settings → Devices → Developer mode** (menu wording may change).
3. Choose **Add Device**, select a nearby gadget advertised as `MuseGadget-XXXXXX`, and follow the pairing confirmation on the device and phone.
4. Set up the device on your trusted **2.4 GHz Wi-Fi** network and allow it to establish its Muse connection.
5. Check that the avatar/UI and connection status appear on the display.

Pairing requires a valid SDK token in the firmware, a supported Muse app experience and available service. Community devices do not carry manufacturer attestation.

## 8. Optional Fish Audio spoken replies

Fish Audio converts the Muse reply **text** to audio online; it is not an offline speech model. Obtain a key from <https://fish.audio/app/api-keys>.

With the board connected over USB, the serial monitor closed, and your terminal in `esp32/`:

```bash
python tools/muse/save_fish_api_key.py
```

The helper prompts with hidden input and saves the key in device NVS. On the device, visit **Settings → Voice Replies**, confirm **Fish Audio API key saved**, and select a configured voice. The project provides configurable voice slots (Muse, Ethan and Sarah); service availability and account limits depend on Fish Audio.

The device's NVS is **not encrypted at rest**, so protect physical access to the device. Prefer the USB/phone setup flow over compiling a Fish Audio key into your public build. Without Fish Audio, reply text can still display on screen.

## 9. Smoke test your installation

With the gadget paired and connected:

- **Boot / Idle:** The custom robot appears and plays a smooth multi-frame Idle animation; blinking continues.
- **Wake word:** Say **“Hey Muse”** near the device. The local detector begins a voice turn.
- **Listening / Thinking:** The robot changes to its respective animated pose while listening and processing.
- **Speaking:** Ask a question and watch the responsive Speaking movement while Fish Audio plays the reply (if configured).
- **Other states:** Check touch reactions, Sleep/Wake and Power-off in normal use. Preserve working settings; do not factory-reset just to test the avatar.

Audio interaction still depends on a working Muse connection; the wake word is on-device, but the overall assistant is **not fully offline**.

## 10. Common problems

| Symptom | Try this |
| --- | --- |
| `cd: no such file or directory: esp32` | You are likely **already inside** `esp32/`. Run `pwd`; use the full repository path when unsure. |
| `idf.py: command not found` | Run `. ~/esp/esp-idf-v6/export.sh` in the current terminal, adjusting the path to your IDF install. |
| ESP-IDF / Python version mismatch | Use the same ESP-IDF 6.0.1 installation and the Python environment that configured the build. Avoid copying an old `build-*` directory between computers. |
| Build succeeds but screen stays blank or shows strange colours | Confirm the board is really the **1.75-B / non-C** and you used **`s3n`**. The `s3` 1.75C profile is different. |
| No USB port | Use a data cable, reconnect, check OS device permissions and close conflicting serial monitors. |
| Muse app cannot pair | Confirm your personal SDK token was configured **before** the build; check Wi-Fi and phone setup. Don't reset pairing or erase NVS as a first remedy. |
| Audio plays but sprite animation is static | Confirm you checked out `feature/smooth-animation` and built it, not another branch or an old binary. |
| Text replies work, but no speech | Save a Fish Audio key, check **Voice Replies**, internet access and Fish Audio service/account status. |
| Need build diagnostics | `tail -n 80 /tmp/muse_build_s3n.log` |

To inspect serial output, activate ESP-IDF and run (replace `PORT`):

```bash
idf.py -B build-muse-waveshare-s3-175 -p PORT monitor
```

Use **Ctrl+]** to exit the ESP-IDF monitor before flashing or saving a Fish Audio key.

## Developers: customising the avatar

- Original and additional **64×64 PNG** sprites live under `esp32/avatar/assets/robot/`.
- The converter is `esp32/avatar/assets/robot/convert_sprites.py` and generates `robot_sprites.h` in the same directory.
- The animation selection / RGB565 renderer lives in `esp32/avatar/muse_pixel.c`; UI state integration is in `esp32/components/muse/muse_ui.c`.
- The generated sprite header is already tracked and **does not need regeneration for a normal clean clone**.
- If you edit sprites, set up Pillow (`python3 -m pip install Pillow` in your chosen virtual environment), regenerate via `python esp32/avatar/assets/robot/convert_sprites.py` **from the repository root**, then rebuild.
- Keep the artwork **64×64**, correctly aligned and transparent; changing palettes or compressing sprites is **not part of the stable setup**.
- When modifying renderer timing, preserve the audio-responsive Speaking path and the display sleep/wake lifecycle. Prefer a separate feature branch and test on hardware before committing.

## Licence and acknowledgements

This fork is based on the [Muse Gadgets SDK](https://github.com/facebookincubator/muse-gadget-sdk) and includes the “Hey Muse” wake-word model from [wobsoriano/hey-muse](https://github.com/wobsoriano/hey-muse). Review the root `LICENSE` and the model licence at `esp32/components/muse/models/HEY-MUSE-LICENSE` when redistributing.
