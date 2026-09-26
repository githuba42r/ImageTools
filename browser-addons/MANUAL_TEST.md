# Browser Addon — Manual Test Plan

The addons (`chrome/`, `firefox/`) have no automated test harness. Run these
checks after any change to `content.js` capture/selection logic. Apply each
case to **both** Chrome and Firefox builds.

Open DevTools → Console while testing. The capture path logs
`[ImageTools] selection capture scale diag:` and
`[ImageTools] full-page capture scale diag:` — use these to confirm the
derived `scaleX/scaleY` match expectations.

## 1. Edge selection (Bug: selection off the screen edge)

Trigger **Capture Selection** on a normal page, then:

| Case | Steps | Expected |
|------|-------|----------|
| 1a | Drag from inside the page **off the left edge**, release the mouse button **outside the browser window**, move back in | Selection completes; ✓ Capture / Reselect / Cancel buttons appear; no page text/content is highlighted |
| 1b | Same dragging off the **right**, **top**, and **bottom** edges | Same as 1a for each edge |
| 1c | Drag a selection that spans content right at the page edge, Capture | Uploaded crop includes the edge content (selection rect was clamped to the viewport, not lost) |
| 1d | Press **Esc** mid-selection and after a selection is drawn | Overlay is removed, no capture |
| 1e | Draw a selection, press **Enter** | Capture proceeds (same as clicking ✓ Capture) |
| 1f | Draw selection → Reselect → draw a new one → Capture | Second selection is the one captured |

Fail signal for the original bug: page content gets highlighted (native text
selection) and/or the action buttons never appear after dragging off the edge.

## 2. DevTools Device Toolbar (Bug: capture broken under device emulation)

Open DevTools → toggle **Device Toolbar**. Test at: iPhone preset,
iPad preset, and **Responsive** with a custom width and a non-1 DPR.

| Case | Steps | Expected |
|------|-------|----------|
| 2a | Device Toolbar on (iPhone) → Capture Visible Area | Uploaded image matches what is on screen |
| 2b | Device Toolbar on (iPhone) → Capture Selection, select a known element, Capture | Uploaded crop is exactly the selected region (not blank, not offset, not zoomed) |
| 2c | Device Toolbar on (iPad) → Capture Full Page on a tall page | Full page assembled with no blank bands, overlap, or misalignment between tiles |
| 2d | Responsive mode, custom DPR (e.g. 2 or 3) → repeat 2b and 2c | Same as 2b/2c |
| 2e | Device Toolbar **off** (normal) → repeat 2b and 2c | Still correct (no regression on the normal path) |
| 2f | Retina/HiDPI host display, Device Toolbar off → 2b and 2c | Correct (regression check for real high-DPI displays) |

In the console diag log, `scaleX`/`scaleY` should equal
`capturedImageWidth / window.innerWidth`. Under device emulation this will
**not** equal `window.devicePixelRatio` — that divergence is exactly the bug
this fix addresses.

## 3. Regression — normal desktop path

| Case | Expected |
|------|----------|
| Capture Visible / Full Page / Selection on a normal desktop tab, DevTools closed | All work as before (Visible / Full Page now via the preview modal, see §4); full-page tiles aligned; selection crop accurate |

## 4. Capture tagging and preview confirmation

Pair the addon with an account that already has a few tagged images. Set a
tag in the popup ("Tag uploads as") before starting.

| Case | Steps | Expected |
|------|-------|----------|
| 4a | Capture Selection, draw a region | Action panel shows a **Tag** input pre-filled with the popup's current tag, and up to 8 recent-tag chips (most recent first) above ✓ Capture / Reselect / Cancel |
| 4b | 4a → click a chip → ✓ Capture | Chip highlights and fills the input; uploaded image carries that tag; popup now shows it as the current tag |
| 4c | 4a → type a brand-new tag → press **Enter** | Captures with the new tag; typing in the input does not trigger page keyboard shortcuts (e.g. `s`/`/` on GitHub) |
| 4d | 4a → clear the tag (×) → Capture | Image uploaded untagged; popup's current tag is cleared |
| 4e | Capture Visible Area (context menu **and** popup button) | Nothing uploads yet; a modal shows the captured image preview, tag picker, ✓ Upload / ✕ Discard. The modal itself is not in the captured image |
| 4f | Capture Full Page on a tall page | Same modal; the preview scrolls to show the whole page |
| 4g | 4e/4f → pick or type a tag → ✓ Upload (or **Enter**) | Button shows "Uploading…", modal closes, "Screenshot uploaded!" notification, image has the tag, popup current tag updated |
| 4h | 4e/4f → ✕ Discard (or **Esc**) | Modal closes, nothing uploaded |
| 4i | Stop the backend, 4e → ✓ Upload | Modal stays open with "Upload failed: …" and a Retry button; Discard still works |
| 4j | Repeat any capture several times on the same tab without reloading | Only one overlay/modal at a time; each action handled once (no duplicate uploads) |
| 4k | Addon paired before `user_id` was stored, or tags endpoint unreachable | Tag input still works; chips are simply absent |
| 4l | Strict-CSP site (e.g. github.com) → 4e | Preview image renders |

