# No longer maintained
[MSC2545](https://github.com/matrix-org/matrix-spec-proposals/pull/2545) has
been accepted into the Matrix spec and most clients already implemented it long
ago.

Importing packs from Telegram is built into the Telegram bridge now, just use
the command, e.g. `!tg import-image-pack https://t.me/addstickers/pusheen02`
(Signal, WhatsApp and Slack also support importing packs). The giphy/klipy proxy
will be maintained as a separate project for gomuks at <https://github.com/gomuks/gifproxy>.

The wiki also has a command to convert existing packs to the MSC2545 format:
<https://github.com/maunium/stickerpicker/wiki/Creating-packs#converting-packs-to-msc2545-format>.

This project still works fine for users who are stuck on Element, but it's
better to use clients that support native Matrix sticker packs.

# Maunium sticker picker
A fast and simple Matrix sticker picker widget. Tested on Element Web, Android & iOS.

## Discussion
Matrix room: [`#stickerpicker:maunium.net`](https://matrix.to/#/#stickerpicker:maunium.net)

## Instructions
For setup and usage instructions, please visit the [wiki](https://github.com/maunium/stickerpicker/wiki):

* [Creating packs](https://github.com/maunium/stickerpicker/wiki/Creating-packs)
* [Enabling the widget](https://github.com/maunium/stickerpicker/wiki/Enabling-the-widget)
* [Hosting on GitHub pages](https://github.com/maunium/stickerpicker/wiki/Hosting-on-GitHub-pages)

If you prefer video tutorials, [Brodie Robertson](https://www.youtube.com/c/BrodieRobertson) has made a great video on setting up the picker and creating some packs: https://youtu.be/Yz3H6KJTEI0.

## Comparison with other sticker pickers

* Scalar is the default integration manager in Element, which can't be self-hosted and only supports predefined sticker packs.
* [Dimension](https://github.com/turt2live/matrix-dimension) is an alternate integration manager. It can be self-hosted, but it's more difficult than Maunium sticker picker.
* Maunium sticker picker is just a sticker picker rather than a full integration manager. It's much simpler than integration managers, but currently has to be set up manually per-user.

| Feature                         | Scalar | Dimension | Maunium sticker picker |
|---------------------------------|--------|-----------|------------------------|
| Free software                   | ❌     | ✔️        | ✔️                     |
| Custom sticker packs            | ❌     | ✔️        | ✔️                     |
| Telegram import                 | ❌     | ✔️        | ✔️                     |
| Works on Element mobiles        | ✔️     | ❌        | ✔️                     |
| Easy multi-user setup           | ✔️     | ✔️        | ❌<sup>[#7][#7]</sup>  |
| Frequently used stickers at top | ❌     | ❌        | ✔️                     |

[#7]: https://github.com/maunium/stickerpicker/issues/7

## Preview
### Element Web
![Element Web](preview-element-web.png)

### Element Android
![Element Android](preview-element-android.png)

### Element iOS (dark theme)
![Element iOS](preview-element-ios.png)

## Local automatic search tags

Run this from the repository root on your AMD Linux machine:

```sh
bash scripts/tag-stickers.sh
```

The first run creates a separate `.venv-tagger`, installs PyTorch's ROCm build,
then automatically downloads [Taggerine](https://huggingface.co/lodestones/taggerine)
when an image needs tagging. The pinned model is trained on e621/Danbooru tags,
including furry and explicit content. No content-rating filter is applied.
Images are processed locally; they are not uploaded to a tagging service.
Model/dependency downloads require internet access the first time.

The model cache defaults to `$XDG_CACHE_HOME/stickerpicker/taggerine`, or
`~/.cache/stickerpicker/taggerine`. Model weights are several GB; allow additional
space for PyTorch and working memory. Weights and the tagging environment are not
part of Git or the website. The script downloads the upstream inference code and
weights at a fixed revision, rather than following changes to `main`.

For the RX 9070, the setup uses the official PyTorch ROCm 7.2 wheel index. Arch
must already have a working AMD driver and access to `/dev/kfd` and `/dev/dri`.
Setup checks GPU availability and runs a small GPU operation. It does not change
system drivers or user groups. If wheels are unavailable for your Python version,
select an installed compatible interpreter, for example
`TAGGER_PYTHON=python3.12 bash scripts/setup-tagger.sh rocm`.
`TORCH_INDEX_URL` can override the ROCm wheel index for a different compatible build.

CPU fallback (slower):

```sh
bash scripts/setup-tagger.sh cpu
bash scripts/tag-stickers.sh --device cpu
```

### Repeat after importing stickers

```sh
bash scripts/tag-stickers.sh
```

Only new/changed images or changed tagging settings are processed. The model is
loaded once per run, only if needed. Every completed sticker is saved atomically,
so rerunning after an interruption resumes work. Cached model files also work
offline. Do not run the importer and tagger concurrently against the same pack.

Useful options:

```sh
# Inspect pending work without installing packages, downloading, or writing files:
bash scripts/tag-stickers.sh --dry-run

# Process only one pack (repeat --pack for multiple packs):
bash scripts/tag-stickers.sh --pack Leo2_0_by_fStikBot.json

# Re-tag everything, even unchanged images:
bash scripts/tag-stickers.sh --force

# Keep more confident tags only:
bash scripts/tag-stickers.sh --threshold 0.5 --max-tags 30
```

By default, the script reads packs listed in `web/packs/index.json` and their
existing local `web/packs/thumbnails` images. Missing images are reported and
produce a nonzero exit status; other images can still complete. Restore missing
thumbnails with the existing `sticker-download-thumbnails` command for that pack.
For animated stickers, tagging describes the still preview available locally.
Remote pack URLs must be downloaded into the packs directory first.

Results are stored in each sticker's `auto_tags` field, including confidence,
model revision, image hash, and settings. You can separately add a `tags` array
for manual descriptions and an `excluded_tags` array to suppress incorrect tags:

```json
{
  "tags": ["comfort", "goodnight"],
  "excluded_tags": ["angry"]
}
```

These manual fields and all other sticker metadata survive re-tagging. Generated
tags are predictions, so review them before publishing. Search matches generated
and manual tags, pack names, sticker text/IDs, and Telegram emoji. Spaces and
underscores are interchangeable; multiple words must all match. This is tag
search, not unrestricted natural-language semantic search.

Commit the scripts, search changes, and updated pack JSON files, then push to your
GitHub Pages deployment source. No model or Python runtime runs on GitHub Pages.
Refresh the picker after deployment to load updated tags.

Developer checks (no model required):

```sh
python3 -m unittest discover -s tests -p 'test_tagger.py'
node --test tests/search.test.mjs
```
