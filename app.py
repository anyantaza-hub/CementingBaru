import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import math, os

# Page config
st.set_page_config(page_title="Digital Twin Cementing — Hybrid Dark", layout="wide")

# CSS Hybrid Dark Premium
st.markdown(
    """
    <style>
    :root{--bg:#0f1720;--panel:#11151a;--card:#0f1724;--muted:#94a3b8;--accent:#0ea5a4;--accent2:#f97316;--text:#e6eef6}
    html, body, [class*="css"]  { background: var(--bg); color:var(--text); }
    .stApp { background: linear-gradient(180deg, #0b1220 0%, #071018 100%); }
    .block-container{padding-top:1.2rem;padding-left:1.2rem;padding-right:1.2rem;}
    .card { background: var(--card); padding: 0.65rem; border-radius:8px; box-shadow: 0 4px 18px rgba(0,0,0,0.4); }
    .muted { color: var(--muted); font-size:0.9rem }
    .small { font-size:0.85rem }
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

# Load CSV
CSV = "sample_slurries.csv"
if not os.path.exists(CSV):
    st.error(f"❌ CSV not found: {CSV}. Upload it to the same folder as app.py.")
    st.stop()

df = pd.read_csv(CSV)

# Required columns check
req = ["name","density_ppg","plastic_viscosity_cP","yield_point_lb100ft2","BHCT_F"]
if not all(c in df.columns for c in req):
    st.error("CSV missing required columns.")
    st.stop()

# Sidebar
with st.sidebar:
    st.markdown("<div class='card'><h3>Digital Twin Cementing</h3><p class='muted'>Hybrid Dark UI</p></div>", unsafe_allow_html=True)
    st.markdown("---")

    slurry = st.selectbox("Select slurry", df["name"].tolist())
    row = df[df["name"] == slurry].iloc[0]

    hole = st.number_input("Hole diameter (in)", 6.0, 20.0, 8.5)
    casing = st.number_input("Casing OD (in)", 4.0, 16.0, 5.5)
    depth = st.slider("Casing depth TD (ft)", 1000, 12000, 3000, 100)
    toc = st.slider("Top of Cement (ft)", 0, depth - 50, int(depth * 0.5), 50)
    rate = st.slider("Pump rate (bbl/min)", 0.5, 18.0, 4.0, 0.1)

    fracture_grad = st.slider("Fracture gradient (ppg)", 12.0, 22.0, 17.0)
    pore_press = st.slider("Pore pressure (ppg)", 9.0, 18.0, 13.5)

    temp = st.number_input("BHCT (°F)", 50, 350, int(row["BHCT_F"]))
    apply_temp = st.checkbox("Apply temperature correction", True)

    st.markdown("---")
    show = st.multiselect("Show panels",
                          ["ECD","Pressure","Rheology","Schematic","Placement"],
                          default=["ECD","Rheology","Schematic"])

# Derived parameters
density0 = float(row["density_ppg"])
pv0 = float(row["plastic_viscosity_cP"])
yp = float(row["yield_point_lb100ft2"])

density = density_temp_correction(density0, temp) if apply_temp else density0
pv = viscosity_temp_correction(pv0, temp) if apply_temp else pv0

ann_area = annulus_area_ft2(hole, casing)
ann_dh = annulus_hydraulic_diameter_ft(hole, casing)

vol_bbl = ann_area * 7.48052 * (depth - toc) / 42.0
pump_time = vol_bbl / rate if rate > 0 else 0.001

# Title
st.markdown("<div class='card'><h2>Digital Twin Cementing — Hybrid Dark</h2></div>", unsafe_allow_html=True)

col1, col2 = st.columns([1.4, 1])

# -----------------------
# ECD PROFILE
# -----------------------
with col1:
    if "ECD" in show:
        st.markdown("<div class='card'><h4>ECD Profile</h4></div>", unsafe_allow_html=True)

        z = np.linspace(1, depth, 400)
        geom = max(0.1, 1 + (0.45 - ann_dh))

        friction_loss = (pv/10.0)*(rate/4.0) + (yp/20.0)
        friction_psi = friction_loss * z/1000.0 * 50.0 * geom
        hydro = 0.052 * density * z
        total = hydro + friction_psi
        ecd = np.nan_to_num(total / (0.052 * z))

        fig, ax = plt.subplots(figsize=(6,5))
        ax.plot(ecd, z, color='#66b2ff', linewidth=2.2, label="ECD")
        ax.axvline(fracture_grad, color="red", linestyle="--", label="Fracture")
        ax.axvline(pore_press, color="green", linestyle="--", label="Pore")

        if pore_press < fracture_grad:
            ax.fill_betweenx(z, pore_press, fracture_grad, color='#0b5', alpha=0.06)

        ax.invert_yaxis()
        ax.set_xlabel("ECD (ppg)")
        ax.set_ylabel("Depth (ft)")
        ax.grid(ls='--', alpha=0.2)
        ax.legend()
        st.pyplot(fig)

# -----------------------
# PRESSURE PLOT
# -----------------------
    if "Pressure" in show:
        st.markdown("<div class='card'><h4>Pressure Components</h4></div>", unsafe_allow_html=True)

        fig2, ax2 = plt.subplots(figsize=(6,3.4))
        ax2.plot(hydro, z, label="Hydrostatic")
        ax2.plot(friction_psi, z, label="Friction")
        ax2.plot(total, z, linewidth=2, label="Total")
        ax2.invert_yaxis()
        ax2.legend()
        ax2.grid(ls='--', alpha=0.2)
        st.pyplot(fig2)

# -----------------------
# RHEOLOGY + SCHEMATIC
# -----------------------
with col2:
    if "Rheology" in show:
        st.markdown("<div class='card'><h4>Bingham Plastic Rheology</h4></div>", unsafe_allow_html=True)
        sr = np.logspace(0, 3, 120)
        tau = yp * 0.4788 + (pv/1000.0)*sr
        fig3, ax3 = plt.subplots(figsize=(4,3))
        ax3.loglog(sr, tau, color="#f7b955")
        ax3.grid(True, which="both", ls="--", alpha=0.25)
        ax3.set_xlabel("Shear Rate (1/s)")
        ax3.set_ylabel("Shear Stress (Pa)")
        st.pyplot(fig3)

    # -----------------------
    # WELL SCHEMATIC — FIXED VERSION
    # -----------------------
    if "Schematic" in show:
        st.markdown("<div class='card'><h4>Well Schematic</h4></div>", unsafe_allow_html=True)

        fig4, ax4 = plt.subplots(figsize=(3,8))
        ax4.set_ylim(depth, 0)
        ax4.set_xlim(0, 3)

        hole_color = '#11151a'
        casing_color = '#1f8ea6'
        cement_color = '#ffb46b'

        # HOLE
        ax4.fill_betweenx([0, depth], 0.2, 2.8, color=hole_color)
        # CASING
        ax4.fill_betweenx([0, depth], 1.0, 2.0, color=casing_color)
        # CEMENT
        ax4.fill_betweenx([toc, depth], 0.2, 1.0, color=cement_color)
        ax4.fill_betweenx([toc, depth], 2.0, 2.8, color=cement_color)

        # Depth ticks every ~10–12 intervals
        tick_int = max(250, depth // 12)
        ticks = list(range(0, depth + 1, tick_int))

        for t in ticks:
            ax4.hlines(t, 0.2, 0.3, color="#888", linewidth=0.8)
            ax4.text(0.32, t, f"{t} ft", color="#ccc", fontsize=8, va="center")

        ax4.axhline(toc, color='yellow', linestyle='--')
        ax4.text(2.85, toc, f"TOC: {int(toc)} ft", color='yellow', fontsize=9)

        ax4.text(2.85, depth, f"TD: {int(depth)} ft", color="#ccc", fontsize=9)

        ax4.axis('off')
        st.pyplot(fig4)

    # -----------------------
    # CEMENT PLACEMENT
    # -----------------------
    if "Placement" in show:
        st.markdown("<div class='card'><h4>Cement Placement Simulation</h4></div>", unsafe_allow_html=True)

        t = st.slider("Time (min)", 0.0, pump_time*1.2, pump_time*0.5)
        frac = min(1, t/pump_time)
        front = depth - frac*(depth - toc)

        fig5, ax5 = plt.subplots(figsize=(3,8))
        ax5.set_ylim(depth, 0)
        ax5.set_xlim(0, 3)

        ax5.fill_betweenx([0, depth], 0.2, 2.8, color=hole_color)
        ax5.fill_betweenx([0, depth], 1.0, 2.0, color=casing_color)
        ax5.fill_betweenx([front, depth], 0.2, 1.0, color=cement_color)
        ax5.fill_betweenx([front, depth], 2.0, 2.8, color=cement_color)

        ax5.axhline(front, color="yellow", linestyle="--")
        ax5.text(2.85, front, f"Front @ {int(front)} ft", color="yellow")

        ax5.axis('off')
        st.pyplot(fig5)
