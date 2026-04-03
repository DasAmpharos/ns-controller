"""NS Controller — State Configurator

Visual tool for defining game states as regions of interest on a live or frozen video frame.
Exports ready-to-use frames.py (Python) or config.json for use in automation scripts.

Run with:
    poetry run streamlit run ns_shiny_hunter/tools/configurator.py
"""

from __future__ import annotations

import base64
import io
import json
import zipfile
from dataclasses import dataclass, field
from typing import Final, Literal

import cv2
import numpy as np
import streamlit as st
import streamlit.elements.image as _st_image_module
from PIL import Image

# ── Compatibility shim ────────────────────────────────────────────────────────
# streamlit-drawable-canvas calls st.elements.image.image_to_url which was
# removed in Streamlit 1.45+.  Patch it back using the current MediaFileManager
# API so the canvas receives a proper server-side URL (the JS prepends the
# Streamlit origin, which works with a path but not with a data: URI).
if not hasattr(_st_image_module, "image_to_url"):
    def _image_to_url(image, width, clamp, channels, output_format, image_key):  # noqa: ANN001
        from streamlit.runtime import Runtime
        buf = io.BytesIO()
        fmt = (output_format or "PNG").upper()
        if fmt == "AUTO":
            fmt = "PNG"
        if image.mode not in ("RGB", "RGBA", "L"):
            image = image.convert("RGB")
        image.save(buf, format=fmt)
        mime = "image/png" if fmt == "PNG" else "image/jpeg"
        return Runtime.instance().media_file_mgr.add(buf.getvalue(), mime, image_key)

    _st_image_module.image_to_url = _image_to_url  # type: ignore[attr-defined]

from streamlit_drawable_canvas import st_canvas  # noqa: E402

from ns_shiny_hunter.frame import (
    CompositeFrameProcessor,
    FrameProcessors,
    ReferenceFrameTemplate,
    ReferenceFrameTemplateMatch,
)
from ns_shiny_hunter.frame_grabber import FrameGrabber
from ns_shiny_hunter.roi import ROI

# ── Constants ─────────────────────────────────────────────────────────────────

CANVAS_DISPLAY_WIDTH: Final = 640

# Ordered pipeline step registry — order matters when building the processor chain.
PIPELINE_STEP_REGISTRY: Final[dict[str, object]] = {
    "gray": FrameProcessors.CVT_COLOR_BGR2GRAY,
    "gaussian_blur": FrameProcessors.GAUSSIAN_BLUR_DEFAULT,
    "median_blur": FrameProcessors.MEDIAN_BLUR_DEFAULT,
    "adaptive_threshold": FrameProcessors.ADAPTIVE_THRESHOLD_DEFAULT,
}

PIPELINE_PRESETS: Final[dict[str, list[str] | None]] = {
    "Text / Dialog": ["gray", "gaussian_blur", "adaptive_threshold"],
    "Full Preprocess": ["gray", "gaussian_blur", "median_blur", "adaptive_threshold"],
    "Grayscale Only": ["gray"],
    "Color Match": [],
    "Custom": None,  # sentinel — user picks steps manually
}

# ROI overlay colours per state index (BGR for OpenCV)
_ROI_COLORS_BGR: Final = [
    (68, 68, 255),    # red
    (68, 255, 68),    # green
    (255, 68, 68),    # blue
    (68, 255, 255),   # yellow
    (255, 68, 255),   # magenta
    (255, 255, 68),   # cyan
]


# ── State config dataclass ─────────────────────────────────────────────────────

@dataclass
class StateConfig:
    name: str = ""
    roi: ROI | None = None
    pipeline_steps: list[str] = field(default_factory=lambda: ["gray", "gaussian_blur", "adaptive_threshold"])
    threshold: float = 0.85
    match_method: Literal["pixel_diff", "template_match"] = "pixel_diff"
    reference_bgr: np.ndarray | None = None
    reference_resolution: tuple[int, int] = (1280, 720)


# ── Processing helpers ────────────────────────────────────────────────────────

def _build_pipeline_processor(state: StateConfig, frame_w: int, frame_h: int) -> CompositeFrameProcessor | None:
    """Build a processor that crops to ROI then applies the configured pipeline steps."""
    if state.roi is None:
        return None
    x, y, w, h = state.roi.to_pixels(frame_w, frame_h)
    processors = [FrameProcessors.crop_rect(x, y, w, h)]
    for step in state.pipeline_steps:
        if step in PIPELINE_STEP_REGISTRY:
            processors.append(PIPELINE_STEP_REGISTRY[step])  # type: ignore[arg-type]
    return CompositeFrameProcessor(*processors)


def _apply_pipeline(frame: np.ndarray, state: StateConfig) -> np.ndarray | None:
    """Crop + process a full frame according to a state's ROI and pipeline."""
    h, w = frame.shape[:2]
    proc = _build_pipeline_processor(state, w, h)
    if proc is None:
        return None
    result = proc.process_frame(frame)
    return result if result.size > 0 else None


def _build_reference_frame(
    state: StateConfig, frame_w: int, frame_h: int
) -> ReferenceFrameTemplate | ReferenceFrameTemplateMatch | None:
    if state.reference_bgr is None or state.roi is None:
        return None
    proc = _build_pipeline_processor(state, frame_w, frame_h)
    if proc is None:
        return None
    if state.match_method == "pixel_diff":
        return ReferenceFrameTemplate(state.reference_bgr, state.threshold, proc, preprocessed=True)
    return ReferenceFrameTemplateMatch(state.reference_bgr, state.threshold, proc, preprocessed=True)


# ── Export ────────────────────────────────────────────────────────────────────

def _encode_png(img: np.ndarray) -> bytes:
    _, buf = cv2.imencode(".png", img)
    return buf.tobytes()


def _pipeline_code_str(state: StateConfig, x: int, y: int, w: int, h: int) -> str:
    step_map = {
        "gray": "FrameProcessors.CVT_COLOR_BGR2GRAY",
        "gaussian_blur": "FrameProcessors.GAUSSIAN_BLUR_DEFAULT",
        "median_blur": "FrameProcessors.MEDIAN_BLUR_DEFAULT",
        "adaptive_threshold": "FrameProcessors.ADAPTIVE_THRESHOLD_DEFAULT",
    }
    parts = [f"FrameProcessors.crop_rect({x}, {y}, {w}, {h})"]
    parts += [step_map[s] for s in state.pipeline_steps if s in step_map]
    if len(parts) == 1:
        return parts[0]
    inner = ",\n            ".join(parts)
    return f"FrameProcessors.all(\n            {inner},\n        )"


def export_python(states: list[StateConfig], class_name: str) -> tuple[str, dict[str, bytes]]:
    """Return (frames.py source code, {relative_path: bytes}) for all complete states."""
    images: dict[str, bytes] = {}
    body_lines: list[str] = []

    for state in states:
        if not state.name or state.roi is None or state.reference_bgr is None:
            continue
        rw, rh = state.reference_resolution
        x, y, w, h = state.roi.to_pixels(rw, rh)
        img_rel = f"refs/{state.name}.png"
        images[img_rel] = _encode_png(state.reference_bgr)
        factory = "template_from_path" if state.match_method == "pixel_diff" else "template_match_from_path"
        pipeline = _pipeline_code_str(state, x, y, w, h)
        flags_arg = "        flags=cv2.IMREAD_GRAYSCALE,\n" if "gray" in state.pipeline_steps else ""
        body_lines.append(
            f"    {state.name} = ReferenceFrames.{factory}(\n"
            f'        _HERE / "{img_rel}",\n'
            f"        threshold={state.threshold},\n"
            f"        frame_processor={pipeline},\n"
            f"{flags_arg}"
            f"    )"
        )

    body = "\n\n".join(body_lines) if body_lines else "    pass"
    source = (
        "# Auto-generated by ns_shiny_hunter configurator — do not edit by hand.\n"
        "import pathlib\n\n"
        "import cv2\n\n"
        "from ns_shiny_hunter.frame import ReferenceFrameEnum, ReferenceFrames, FrameProcessors\n\n"
        "_HERE = pathlib.Path(__file__).parent\n\n\n"
        f"class {class_name}ReferenceFrames(ReferenceFrameEnum):\n"
        f"{body}\n"
    )
    return source, images


def export_json(states: list[StateConfig]) -> tuple[dict, dict[str, bytes]]:
    """Return (config dict, {relative_path: bytes}) for all states that have names."""
    images: dict[str, bytes] = {}
    state_list = []

    for state in states:
        if not state.name:
            continue
        entry: dict = {
            "name": state.name,
            "pipeline": state.pipeline_steps,
            "threshold": state.threshold,
            "match_method": state.match_method,
        }
        if state.roi:
            entry["roi"] = state.roi.to_dict()
            entry["reference_resolution"] = list(state.reference_resolution)
        if state.reference_bgr is not None:
            img_rel = f"refs/{state.name}.png"
            images[img_rel] = _encode_png(state.reference_bgr)
            entry["reference_image"] = img_rel
        state_list.append(entry)

    return {"states": state_list}, images


def _make_zip(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in files.items():
            zf.writestr(name, data)
    return buf.getvalue()


# ── Session state ─────────────────────────────────────────────────────────────

def _init_session():
    defaults: dict = {
        "frame_grabber": None,
        "frozen_frame": None,
        "show_live": True,
        "states": [],
        "selected_idx": None,
        "_canvas_ver": 0,
        "_export_python_zip": None,
        "_export_json_zip": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _states() -> list[StateConfig]:
    return st.session_state.states  # type: ignore[return-value]


def _selected() -> StateConfig | None:
    idx = st.session_state.selected_idx
    states = _states()
    if idx is None or idx >= len(states):
        return None
    return states[idx]


# ── Sidebar ───────────────────────────────────────────────────────────────────

def _render_sidebar() -> None:
    with st.sidebar:
        st.title("📹 Source")

        source_type = st.radio("Type", ["Device index", "Path / URL"], horizontal=True, label_visibility="collapsed")
        if source_type == "Device index":
            raw_source: int | str = int(st.number_input("Device index", min_value=0, max_value=10, value=0, step=1))
        else:
            raw_source = st.text_input("Path or URL", placeholder="/dev/video0  |  rtsp://...  |  http://...")

        c1, c2 = st.columns(2)
        frame_w = c1.number_input("Width", value=1280, step=1)
        frame_h = c2.number_input("Height", value=720, step=1)
        fps = st.number_input("FPS", value=60, step=1)

        fg: FrameGrabber | None = st.session_state.frame_grabber
        connected = fg is not None and fg.running.is_set()

        if st.button("▶ Connect", use_container_width=True, type="primary"):
            if fg is not None:
                fg.stop()
            new_fg = FrameGrabber(
                source=raw_source,
                width=int(frame_w),
                height=int(frame_h),
                fps=int(fps),
                imshow=False,
            )
            new_fg.start()
            st.session_state.frame_grabber = new_fg
            st.session_state.frozen_frame = None
            st.session_state.show_live = True
            st.rerun()

        if st.button("■ Disconnect", use_container_width=True, disabled=not connected):
            if fg:
                fg.stop()
            st.session_state.frame_grabber = None
            st.session_state.show_live = True
            st.rerun()

        if connected:
            st.success(f"Connected · {int(fg.width)}×{int(fg.height)} @ {int(fg.fps)} fps")  # type: ignore[union-attr]
        else:
            st.info("Not connected.")

        st.divider()
        st.title("💾 Export")

        class_name = st.text_input("Class name", value="MyScript", help="Generates {ClassName}ReferenceFrames")
        ready = [s for s in _states() if s.name and s.roi and s.reference_bgr is not None]
        st.caption(f"{len(ready)}/{len(_states())} states ready (need name + ROI + reference image)")

        ec1, ec2 = st.columns(2)
        if ec1.button("🐍 Python", use_container_width=True, disabled=not ready):
            code, imgs = export_python(ready, class_name)
            files = {"frames.py": code.encode()} | imgs
            st.session_state["_export_python_zip"] = _make_zip(files)
            st.rerun()
        if ec2.button("📄 JSON", use_container_width=True, disabled=not ready):
            cfg, imgs = export_json(ready)
            files = {"config.json": json.dumps(cfg, indent=2).encode()} | imgs
            st.session_state["_export_json_zip"] = _make_zip(files)
            st.rerun()

        if st.session_state["_export_python_zip"]:
            st.download_button(
                "⬇ Download frames.py + refs/",
                data=st.session_state["_export_python_zip"],
                file_name=f"{class_name}_frames.zip",
                mime="application/zip",
                use_container_width=True,
            )
        if st.session_state["_export_json_zip"]:
            st.download_button(
                "⬇ Download config.json + refs/",
                data=st.session_state["_export_json_zip"],
                file_name=f"{class_name}_config.zip",
                mime="application/zip",
                use_container_width=True,
            )


# ── Left column — video / canvas area ─────────────────────────────────────────

@st.fragment(run_every=0.1)
def _render_live_feed() -> None:
    fg: FrameGrabber | None = st.session_state.frame_grabber
    if fg is None or not fg.running.is_set():
        st.info("Connect to a video source to see the live feed.")
        return
    frame = fg.get_frame()
    if frame is None:
        st.warning("Waiting for first frame…")
        return
    _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
    b64 = base64.b64encode(buf).decode()
    st.html(f'<img src="data:image/jpeg;base64,{b64}" style="width:100%;height:auto;">')


def _annotate_frozen(frozen: np.ndarray, selected_idx: int | None) -> np.ndarray:
    """Draw all state ROIs on the frozen frame using OpenCV, highlighting the selected one."""
    annotated = frozen.copy()
    h, w = annotated.shape[:2]
    for i, state in enumerate(_states()):
        if state.roi is None:
            continue
        color = _ROI_COLORS_BGR[i % len(_ROI_COLORS_BGR)]
        thickness = 3 if i == selected_idx else 1
        sx, sy, sw, sh = state.roi.to_pixels(w, h)
        cv2.rectangle(annotated, (sx, sy), (sx + sw, sy + sh), color, thickness)
        label = state.name or f"state_{i}"
        cv2.putText(annotated, label, (sx + 2, max(10, sy - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)
    return annotated


def _render_canvas() -> None:
    frozen: np.ndarray | None = st.session_state.frozen_frame
    if frozen is None:
        st.info("No frozen frame — click **Freeze Frame** while connected.")
        return

    h, w = frozen.shape[:2]
    display_w = CANVAS_DISPLAY_WIDTH
    display_h = int(display_w * h / w)
    scale = w / display_w

    selected_idx: int | None = st.session_state.selected_idx
    annotated = _annotate_frozen(frozen, selected_idx)
    pil_img = Image.fromarray(cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)).resize(
        (display_w, display_h), Image.LANCZOS
    )

    canvas_key = f"canvas_v{st.session_state._canvas_ver}_s{selected_idx}"
    canvas_result = st_canvas(
        background_image=pil_img,
        drawing_mode="rect",
        stroke_color="#FF0000",
        fill_color="rgba(255, 0, 0, 0.12)",
        stroke_width=2,
        height=display_h,
        width=display_w,
        key=canvas_key,
        display_toolbar=True,
    )

    if selected_idx is None:
        st.caption("Select or add a state on the right, then draw a rectangle to set its ROI.")
        return

    objects = (canvas_result.json_data or {}).get("objects", [])
    if objects:
        obj = objects[-1]
        cx = float(obj.get("left", 0))
        cy = float(obj.get("top", 0))
        cw = float(obj.get("width", 0)) * float(obj.get("scaleX", 1))
        ch = float(obj.get("height", 0)) * float(obj.get("scaleY", 1))
        new_roi = ROI.from_pixels(int(cx * scale), int(cy * scale), int(cw * scale), int(ch * scale), w, h)
        state = _states()[selected_idx]
        if state.roi != new_roi:
            state.roi = new_roi
            state.reference_resolution = (w, h)

    state = _states()[selected_idx]
    if state.roi:
        sx, sy, sw, sh = state.roi.to_pixels(w, h)
        st.caption(
            f"ROI at {w}×{h}: x={sx} y={sy} w={sw} h={sh} "
            f"· relative: ({state.roi.x:.4f}, {state.roi.y:.4f}, {state.roi.w:.4f}, {state.roi.h:.4f})"
        )
    else:
        st.caption("Draw a rectangle on the frame to set the ROI for the selected state.")


def _render_left_column() -> None:
    fg: FrameGrabber | None = st.session_state.frame_grabber
    connected = fg is not None and fg.running.is_set()

    b1, b2 = st.columns(2)
    if b1.button("❄️ Freeze Frame", disabled=not connected, use_container_width=True):
        frame = fg.get_frame() if fg else None  # type: ignore[union-attr]
        if frame is not None:
            st.session_state.frozen_frame = frame
            st.session_state.show_live = False
            st.session_state._canvas_ver += 1
        st.rerun()
    if b2.button("🔴 Back to Live", disabled=not connected, use_container_width=True):
        st.session_state.show_live = True
        st.rerun()

    if st.session_state.show_live:
        _render_live_feed()
    else:
        _render_canvas()


# ── Right column — state editor ───────────────────────────────────────────────

@st.fragment(run_every=0.5)
def _render_match_score() -> None:
    fg: FrameGrabber | None = st.session_state.frame_grabber
    state = _selected()
    if fg is None or not fg.running.is_set() or state is None or state.reference_bgr is None or state.roi is None:
        return

    frame = fg.get_frame()
    if frame is None:
        return

    fh, fw = frame.shape[:2]
    ref = _build_reference_frame(state, fw, fh)
    if ref is None:
        return

    score = ref.get_percent_match(frame)
    matches = score >= state.threshold
    st.markdown("**Live match score**")
    st.progress(min(score, 1.0))
    if matches:
        st.success(f"✓  {score:.4f}  (threshold {state.threshold:.2f})")
    else:
        st.error(f"✗  {score:.4f}  (threshold {state.threshold:.2f})")


def _render_pipeline_preview(state: StateConfig) -> None:
    frozen: np.ndarray | None = st.session_state.frozen_frame
    if frozen is None or state.roi is None:
        return
    fh, fw = frozen.shape[:2]
    sx, sy, sw, sh = state.roi.to_pixels(fw, fh)
    raw_crop = frozen[sy : sy + sh, sx : sx + sw]
    processed = _apply_pipeline(frozen, state)
    if raw_crop.size == 0 or processed is None or processed.size == 0:
        return
    pc1, pc2 = st.columns(2)
    pc1.image(cv2.cvtColor(raw_crop, cv2.COLOR_BGR2RGB), caption="Raw crop", width='stretch')
    if processed.ndim == 2:
        pc2.image(processed, caption="Processed", width='stretch', clamp=True)
    else:
        pc2.image(cv2.cvtColor(processed, cv2.COLOR_BGR2RGB), caption="Processed", width='stretch')


def _render_state_editor() -> None:
    states = _states()
    selected_idx: int | None = st.session_state.selected_idx

    st.subheader("States")
    if st.button("＋ Add State", use_container_width=True):
        states.append(StateConfig(name=f"STATE_{len(states)}"))
        st.session_state.selected_idx = len(states) - 1
        st.session_state._canvas_ver += 1
        st.rerun()

    for i, state in enumerate(states):
        has_roi = state.roi is not None
        has_ref = state.reference_bgr is not None
        icon = "✓" if (has_roi and has_ref) else ("◑" if has_roi else "○")
        lc, rc = st.columns([5, 1])
        btn_type = "primary" if i == selected_idx else "secondary"
        if lc.button(f"{icon}  {state.name or '(unnamed)'}", key=f"sel_{i}", use_container_width=True, type=btn_type):
            st.session_state.selected_idx = i
            st.session_state._canvas_ver += 1
            st.rerun()
        if rc.button("✕", key=f"del_{i}"):
            states.pop(i)
            if selected_idx == i:
                st.session_state.selected_idx = None
            elif selected_idx is not None and selected_idx > i:
                st.session_state.selected_idx -= 1
            st.session_state._canvas_ver += 1
            st.rerun()

    state = _selected()
    if state is None:
        st.info("Select or add a state above to edit it.")
        return

    st.divider()
    st.markdown(f"**Editing: {state.name or '(unnamed)'}**")

    # Name
    new_name = st.text_input("State name", value=state.name, key=f"name_{selected_idx}")
    if new_name != state.name:
        state.name = new_name

    # ROI summary
    if state.roi:
        rw, rh = state.reference_resolution
        sx, sy, sw, sh = state.roi.to_pixels(rw, rh)
        st.caption(f"ROI at {rw}×{rh}: ({sx},{sy})→({sx+sw},{sy+sh}) — redraw on the frame to update")
    else:
        st.caption("No ROI — freeze a frame and draw a rectangle on the left.")

    # Pipeline
    st.markdown("**Pipeline**")
    preset_names = list(PIPELINE_PRESETS.keys())
    current_preset = next(
        (name for name, steps in PIPELINE_PRESETS.items() if steps == state.pipeline_steps),
        "Custom",
    )
    chosen = st.selectbox(
        "Preset",
        preset_names,
        index=preset_names.index(current_preset) if current_preset in preset_names else 0,
        key=f"preset_{selected_idx}",
    )
    if PIPELINE_PRESETS[chosen] is not None:
        state.pipeline_steps = list(PIPELINE_PRESETS[chosen])  # type: ignore[arg-type]
    else:
        state.pipeline_steps = st.multiselect(
            "Steps",
            list(PIPELINE_STEP_REGISTRY.keys()),
            default=state.pipeline_steps,
            key=f"steps_{selected_idx}",
        )

    _render_pipeline_preview(state)

    # Match method
    st.markdown("**Match method**")
    method_idx = 0 if state.match_method == "pixel_diff" else 1
    method = st.radio(
        "Method",
        ["pixel_diff", "template_match"],
        index=method_idx,
        horizontal=True,
        format_func=lambda x: "Pixel diff (absdiff)" if x == "pixel_diff" else "Template match (NCC)",
        key=f"method_{selected_idx}",
        label_visibility="collapsed",
    )
    state.match_method = method  # type: ignore[assignment]

    # Threshold
    state.threshold = float(
        st.slider("Threshold", 0.50, 1.00, state.threshold, 0.01, key=f"thresh_{selected_idx}")
    )

    # Reference image
    st.markdown("**Reference image**")
    frozen: np.ndarray | None = st.session_state.frozen_frame
    rc1, rc2 = st.columns(2)
    if rc1.button(
        "📸 Capture from frozen ROI",
        key=f"capture_{selected_idx}",
        disabled=frozen is None or state.roi is None,
        use_container_width=True,
    ):
        processed = _apply_pipeline(frozen, state)  # type: ignore[arg-type]
        if processed is not None:
            state.reference_bgr = processed
            state.reference_resolution = (frozen.shape[1], frozen.shape[0])  # type: ignore[union-attr]

    uploaded = rc2.file_uploader(
        "Load image", type=["jpg", "png"], key=f"upload_{selected_idx}", label_visibility="collapsed"
    )
    if uploaded:
        arr = np.frombuffer(uploaded.read(), np.uint8)
        loaded = cv2.imdecode(arr, cv2.IMREAD_UNCHANGED)
        if loaded is not None:
            state.reference_bgr = loaded

    if state.reference_bgr is not None:
        ref = state.reference_bgr
        if ref.ndim == 2:
            st.image(ref, caption="Stored reference", width='stretch', clamp=True)
        else:
            st.image(cv2.cvtColor(ref, cv2.COLOR_BGR2RGB), caption="Stored reference", width='stretch')

    _render_match_score()


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    st.set_page_config(
        page_title="NS Controller — State Configurator",
        page_icon="🎮",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    _init_session()
    _render_sidebar()

    st.title("🎮 State Configurator")
    st.caption(
        "Connect to a video source · freeze a frame · draw rectangles to define ROIs · "
        "tune the pipeline and threshold · export as Python or JSON."
    )

    left_col, right_col = st.columns([6, 4])
    with left_col:
        _render_left_column()
    with right_col:
        _render_state_editor()


if __name__ == "__main__":
    main()
