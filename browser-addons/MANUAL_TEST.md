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
| Capture Visible / Full Page / Selection on a normal desktop tab, DevTools closed | All work as before; full-page tiles aligned; selection crop accurate |
