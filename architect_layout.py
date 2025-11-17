# app.py
import streamlit as st
import numpy as np
import plotly.graph_objects as go
import io
import os

# Detect Streamlit Cloud (prevents Kaleido errors)
IS_CLOUD = os.environ.get("STREAMLIT_SERVER_STATUS", "") != ""

# -----------------------------------------------------
# Streamlit Setup
# -----------------------------------------------------
st.set_page_config(layout="wide", page_title="3D Architectural Layout Generator")
st.title("🏠 Fast 3D Architectural Layout Generator with Download")

# -----------------------------------------------------
# Sidebar Inputs
# -----------------------------------------------------
with st.sidebar:
    st.header("Inputs")
    PLOT_WIDTH = st.number_input("Plot width (m)", value=14.0)
    PLOT_DEPTH = st.number_input("Plot depth (m)", value=24.0)
    front_setback = st.number_input("Front setback (m)", value=4.5)
    rear_setback = st.number_input("Rear setback (m)", value=3.0)
    left_setback = st.number_input("Left setback (m)", value=2.0)
    right_setback = st.number_input("Right setback (m)", value=2.0)
    grid_snap_cm = st.number_input("Grid snap (cm)", value=50)

    st.subheader("Car Porch")
    car_w = st.number_input("Width (m)", value=3.2)
    car_d = st.number_input("Depth (m)", value=5.5)

    st.subheader("Room Requirements")
    bedroom_area = st.number_input("Bedroom min area (m²)", value=12.0)
    bedrooms_count = st.number_input("Bedrooms count", value=3, step=1)
    bath_area = st.number_input("Bathroom area (m²)", value=4.0)
    lounge_area = st.number_input("Lounge area (m²)", value=20.0)

    generate_btn = st.button("Generate Layout")

# -----------------------------------------------------
# Helper Functions
# -----------------------------------------------------
def to_grid(meters, snap_cm):
    cell = snap_cm / 100.0
    return max(1, int(round(meters / cell))), cell

def area_to_dims(area, aspect_ratio=1.3):
    w = (area * aspect_ratio) ** 0.5
    h = area / w
    return w, h

def cuboid_coords(x, y, dx, dy, dz):
    X = [x, x+dx, x+dx, x, x, x+dx, x+dx, x]
    Y = [y, y, y+dy, y+dy, y, y, y+dy, y+dy]
    Z = [0, 0, 0, 0, dz, dz, dz, dz]
    I = [0,0,0,4,4,7,1,1,2,3,5,6]
    J = [1,2,3,5,6,4,5,2,6,7,6,7]
    K = [2,3,1,6,7,5,2,3,7,4,7,5]
    return X, Y, Z, I, J, K

# -----------------------------------------------------
# Main Logic
# -----------------------------------------------------
if generate_btn:
    grid_w, cell_m = to_grid(PLOT_WIDTH, grid_snap_cm)
    grid_h, _ = to_grid(PLOT_DEPTH, grid_snap_cm)

    left_c, _ = to_grid(left_setback, grid_snap_cm)
    right_c, _ = to_grid(right_setback, grid_snap_cm)
    front_c, _ = to_grid(front_setback, grid_snap_cm)
    rear_c, _ = to_grid(rear_setback, grid_snap_cm)

    build_w = grid_w - left_c - right_c
    build_h = grid_h - front_c - rear_c

    if build_w <= 0 or build_h <= 0:
        st.error("Setbacks too large — no buildable space.")
        st.stop()

    # Rooms
    rooms = [("Car Porch", car_w, car_d)]
    lw, lh = area_to_dims(lounge_area)
    rooms.append(("Lounge", lw, lh))

    for i in range(1, bedrooms_count + 1):
        bw, bh = area_to_dims(bedroom_area)
        rooms.append((f"Bedroom {i}", bw, bh))

    bw, bh = area_to_dims(bath_area)
    rooms.append(("Bath", bw, bh))

    rooms.sort(key=lambda x: x[1]*x[2], reverse=True)

    layout = {}
    cursor_x = 0
    cursor_y = 0
    max_row_height = 0

    for name, w_m, h_m in rooms:
        w_cells = max(1, int(round(w_m / cell_m)))
        h_cells = max(1, int(round(h_m / cell_m)))

        if cursor_x + w_cells > build_w:
            cursor_x = 0
            cursor_y += max_row_height
            max_row_height = 0

        if cursor_y + h_cells > build_h:
            st.warning(f"{name} cannot fit in buildable area!")
            continue

        layout[name] = (cursor_x, cursor_y, w_cells, h_cells)
        cursor_x += w_cells
        max_row_height = max(max_row_height, h_cells)

    built_area = sum(w*h*cell_m*cell_m for (_, _, w, h) in layout.values())
    total_area = PLOT_WIDTH * PLOT_DEPTH
    coverage = built_area / total_area * 100

    st.success(f"Coverage Achieved: **{coverage:.1f}%**")

    # -----------------------------------------------------
    # Plotly 3D Layout
    # -----------------------------------------------------
    cmap = {"Car Porch": "#8ecae6", "Lounge": "#ffb703", "Bath": "#9b2226"}
    for i in range(1, bedrooms_count+1):
        cmap[f"Bedroom {i}"] = "#bde0fe"

    fig = go.Figure()
    room_height = 3.0

    for name, (x, y, w, h) in layout.items():
        ox, oy = x*cell_m, y*cell_m
        dx, dy = w*cell_m, h*cell_m
        dz = room_height

        X, Y, Z, I, J, K = cuboid_coords(ox, oy, dx, dy, dz)

        fig.add_trace(go.Mesh3d(
            x=X, y=Y, z=Z, i=I, j=J, k=K,
            color=cmap.get(name, "#cccccc"),
            opacity=0.7, flatshading=True,
            name=name, hovertext=name, hoverinfo="text"
        ))

        fig.add_trace(go.Scatter3d(
            x=[ox+dx/2], y=[oy+dy/2], z=[dz+0.1],
            text=[name], mode="text"
        ))

    fig.update_layout(
        scene=dict(
            xaxis_title="Width (m)",
            yaxis_title="Depth (m)",
            zaxis_title="Height (m)",
            aspectmode="data"
        ),
        margin=dict(l=0, r=0, t=0, b=0)
    )

    st.plotly_chart(fig, use_container_width=True)

    # -----------------------------------------------------
    # Downloads (Disabled on Streamlit Cloud)
    # -----------------------------------------------------
    if IS_CLOUD:
        st.warning("⚠️ File download is disabled on Streamlit Cloud (Chromium not available). Run locally to enable PDF/PNG/SVG export.")
    else:
        st.info("📥 Downloads available (running locally).")

        # PDF
        pdf_buffer = io.BytesIO()
        fig.write_image(pdf_buffer, format="pdf")
        pdf_buffer.seek(0)
        st.download_button(
            "Download PDF", pdf_buffer, "3D_layout.pdf", "application/pdf"
        )

        # PNG
        png_buffer = io.BytesIO()
        fig.write_image(png_buffer, format="png")
        png_buffer.seek(0)
        st.download_button(
            "Download PNG", png_buffer, "3D_layout.png", "image/png"
        )

        # SVG
        svg_buffer = io.BytesIO()
        fig.write_image(svg_buffer, format="svg")
        svg_buffer.seek(0)
        st.download_button(
            "Download SVG", svg_buffer, "3D_layout.svg", "image/svg+xml"
        )
