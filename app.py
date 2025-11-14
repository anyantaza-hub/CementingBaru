import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import math
import os

# Page config
st.set_page_config(page_title="Digital Twin Cementing — Hybrid Dark", layout="wide")

# Inject hybrid dark CSS
st.markdown(
    """
    <style>
    :root{--bg:#0f1720;--panel:#11151a;--card:#0f1724;--muted:#94a3b8;--accent:#0ea5a4;--accent2:#f97316;--text:#e6eef6}
    html, body, [class*="css"]  { background: var(--bg); color:var(--text); }
    .stApp { background: linear-gradient(180deg, #0b1220 0%, #071018 100%); }
    .block-container{padding-top:1.25rem;padding-left:1.25rem;padding-right:1.25rem;}
    .card { background: var(--card); padding: 0.65rem; border-radius:8px; box-shadow: 0 6px 18px rgba(3,6,12,0.6); }
    .muted { color: var(--muted); font-size:0.9rem }
    .small { font-size:0.9rem }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True
)

# Utility functions
def density_temp_correction(ppg, T, T_ref=150.0):
    rho_ref = ppg * 7.48052
    alpha = 0.00028
    rho = rho_ref * (1 - alpha * (T - T_ref))
    return rho / 7.48052

def viscosity_temp_correction(pv_cP, T, T_ref=150.0):
    factor = np.exp(-0.015 * (T - T_ref))
    return max(0.001, pv_cP * factor)

def annulus_area_ft2(hole_in, casing_in):
    hole_ft = hole_in/12.0
    casing_ft = casing_in/12.0
    return math.pi * (hole_ft**2 - casing_ft**2) / 4.0

def annulus_hydraulic_diameter_ft(hole_in, casing_in):
    return max(0.0001, (hole_in - casing_in) / 12.0)

# Load CSV safely
CSV = "sample_slurries.csv"
if not os.path.exists(CSV):
    st.error(f"CSV not found: {CSV} — upload to same folder as app.py")
    st.stop()

df = pd.read_csv(CSV)

# Sidebar inputs
with st.sidebar:
    st.image("logo.png", width=110)
    st.markdown("---")

    st.subheader("Operation inputs")
    slurry = st.selectbox("Select slurry", df["name"].tolist())
    row = df[df["name"] == slurry].iloc[0]

    hole = st.number_input("Hole diameter (in)", 6.0, 20.0, 8.5, 0.1)
    casing = st.number_input("Casing OD (in)", 4.0, 16.0, 5.5, 0.1)
    depth = st.slider("Casing depth TD (ft)", 1000, 12000, 3000, 100)
    toc = st.slider("Top of Cement (ft)", 0, depth - 50, int(depth * 0.5), 50)
    rate = st.slider("Pump rate (bbl/min)", 0.5, 18.0, 4.0, 0.1)
    fracture_grad = st.slider("Fracture gradient (ppg)", 12.0, 22.0, 17.0, 0.1)
    pore_press = st.slider("Pore pressure (ppg)", 9.0, 18.0, 13.5, 0.1)
    temp = st.number_input("BHCT (°F)", 50, 350, int(row.get("BHCT_F", 150)))
    apply_temp = st.checkbox("Apply thermal correction", True)

    st.markdown("---")
    st.subheader("Display options")
    show = st.multiselect(
        "Show panels",
        ["ECD", "Pressure", "Rheology", "Schematic", "Placement"],
        default=["ECD", "Rheology", "Schematic"]
    )

# Derived values
density0 = row["density_ppg"]
pv0 = row["plastic_viscosity_cP"]
yp = row["yield_point_lb100ft2"]

density = density_temp_correction(density0, temp) if apply_temp else density0
pv = viscosity_temp_correction(pv0, temp) if apply_temp else pv0

ann_area = annulus_area_ft2(hole, casing)
ann_dh = annulus_hydraulic_diameter_ft(hole, casing)
vol_bbl = ann_area * 7.48052 * (depth - toc) / 42.0
pump_time = vol_bbl / rate if rate > 0 else 0.0

# Header logo
st.image("logo.png", width=150)

# Layout columns
col1, col2 = st.columns([1.4, 1])

# ---------------------------
# COLUMN 1
# ---------------------------
with col1:

    # ECD PROFILE
    if "ECD" in show:
        depth_arr = np.linspace(1, depth, 400)

        geom = max(0.1, 1 + (0.45 - ann_dh))
        friction = (pv/10.0)*(rate/4.0) + (yp/20.0)

        friction_psi = friction * depth_arr/1000.0 * 50.0 * geom
        hydro_psi = 0.052 * density * depth_arr
        total_psi = hydro_psi + friction_psi
        ecd = total_psi / (0.052 * depth_arr)

        st.markdown("<div class='card'><h4>ECD Profile</h4></div>", unsafe_allow_html=True)
        fig, ax = plt.subplots(figsize=(6, 5))
        ax.plot(ecd, depth_arr, linewidth=2, color='#66b2ff')

        if fracture_grad > pore_press:
            ax.fill_betweenx(depth_arr, pore_press, fracture_grad, color="#0b5", alpha=0.1)

        ax.axvline(fracture_grad, color="#ff6b6b", linestyle="--")
        ax.axvline(pore_press, color="#66ffb3", linestyle="--")

        ax.invert_yaxis()
        ax.grid(ls="--", alpha=0.2)
        st.pyplot(fig)

    # PRESSURE PROFILE
    if "Pressure" in show:
        st.markdown("<div class='card'><h4>Pressure Components</h4></div>", unsafe_allow_html=True)
        fig2, ax2 = plt.subplots(figsize=(6, 3.4))
        ax2.plot(hydro_psi, depth_arr, label="Hydrostatic")
        ax2.plot(friction_psi, depth_arr, label="Friction")
        ax2.plot(total_psi, depth_arr, label="Total", linewidth=2)
        ax2.invert_yaxis()
        ax2.grid(ls="--", alpha=0.2)
        ax2.legend()
        st.pyplot(fig2)

# ---------------------------
# COLUMN 2
# ---------------------------
with col2:

    # RHEOLOGY
    if "Rheology" in show:
        st.markdown("<div class='card'><h4>Rheology Curve</h4></div>", unsafe_allow_html=True)
        sr = np.logspace(0, 3, 120)
        yp_Pa = yp * 0.4788
        shear = yp_Pa + (pv/1000.0) * sr
        fig3, ax3 = plt.subplots(figsize=(4, 3))
        ax3.loglog(sr, shear)
        ax3.grid(True, which="both", ls="--", alpha=0.2)
        st.pyplot(fig3)

    # WELL SCHEMATIC (FIXED)
    if "Schematic" in show:
    st.markdown("<div class='card'><h4>Well Schematic</h4></div>", unsafe_allow_html=True)

    fig4, ax4 = plt.subplots(figsize=(3.8, 10))

    # Axis limits
    ax4.set_ylim(depth, 0)
    ax4.set_xlim(0, 3)

    # Colors
    hole_color = "#0a0f12"
    casing_color = "#1f8ea6"
    cement_color = "#ffb46b"

    # Draw geometry
    ax4.fill_betweenx([0, depth], 0.2, 2.8, color=hole_color)          # Hole
    ax4.fill_betweenx([0, depth], 1.0, 2.0, color=casing_color)        # Casing
    ax4.fill_betweenx([toc, depth], 0.2, 1.0, color=cement_color)      # Cement LHS
    ax4.fill_betweenx([toc, depth], 2.0, 2.8, color=cement_color)      # Cement RHS

    # TOC & TD lines
    ax4.axhline(toc, color="#ffd580", linestyle="--", linewidth=1)
    ax4.axhline(depth, color="#ffd580", linestyle="--", linewidth=1)

    # Depth ticks every 500 ft
    tick_step = 500
    ticks = np.arange(0, depth + tick_step, tick_step)
    ax4.set_yticks(ticks)
    ax4.set_yticklabels([f"{int(t)} ft" for t in ticks], color="white")

    # Add annotation inside axis (safe)
    ax4.text(2.1, toc, f"TOC = {int(toc)} ft", color="white", fontsize=10, va="center")
    ax4.text(2.1, depth, f"TD = {int(depth)} ft", color="white", fontsize=10, va="center")

    # Style cleanup
    ax4.tick_params(axis='y', colors='white')
    ax4.tick_params(axis='x', colors='white')
    ax4.set_xticks([])
    ax4.grid(axis='y', linestyle='--', alpha=0.2)

    st.pyplot(fig4)


    # PLACEMENT ANIMATION
    if "Placement" in show:
        st.markdown("<div class='card'><h4>Placement Simulation</h4></div>", unsafe_allow_html=True)

        t = st.slider("Time", 0.0, pump_time * 1.2, pump_time, 0.1)
        frac = min(1, t / pump_time)
        front = depth - frac * (depth - toc)

        fig5, ax5 = plt.subplots(figsize=(3.3, 8))
        ax5.set_ylim(depth, 0)
        ax5.set_xlim(0, 3)

        ax5.fill_betweenx([0, depth], 0.2, 2.8, color="#0a0f12")
        ax5.fill_betweenx([0, depth], 1.0, 2.0, color="#1f8ea6")
        ax5.fill_betweenx([front, depth], 0.2, 1.0, color="#ffb46b")
        ax5.fill_betweenx([front, depth], 2.0, 2.8, color="#ffb46b")

        ax5.axhline(front, color="#ffd580", ls="--")
        ax5.text(2.9, front, f"Front {int(front)} ft", color="white")
        ax5.axis("off")

        st.pyplot(fig5)

# Footer
st.markdown("<p class='muted small'>Prototype for educational use — hybrid dark UI</p>", unsafe_allow_html=True)
