import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import math, os

# Page config
st.set_page_config(
    page_title="Digital Twin Cementing — Hybrid Dark",
    layout="wide"
)

# Hybrid Dark CSS
st.markdown("""
    <style>
    :root{
        --bg:#0f1720;--panel:#11151a;--card:#0f1724;
        --muted:#94a3b8;--accent:#0ea5a4;--accent2:#f97316;
        --text:#e6eef6
    }
    html, body, [class*="css"]  { background: var(--bg); color:var(--text); }
    .stApp { background: linear-gradient(180deg, #0b1220 0%, #071018 100%); }
    .block-container{padding-top:1.25rem;padding-left:1.25rem;padding-right:1.25rem;}
    .card { background: var(--card); padding: 0.65rem; border-radius:8px;
        box-shadow: 0 6px 18px rgba(3,6,12,0.6); }
    .muted { color: var(--muted); font-size:0.9rem }
    .small { font-size:0.9rem }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# Utility functions
def density_temp_correction(ppg, T, T_ref=150.0):
    rho_ref = ppg * 7.48052
    alpha = 0.00028
    rho = rho_ref * (1 - alpha * (T - T_ref))
    return rho / 7.48052

def viscosity_temp_correction(pv_cP, T, T_ref=150.0):
    return max(0.001, pv_cP * np.exp(-0.015 * (T - T_ref)))

def annulus_area_ft2(hole_in, casing_in):
    hole_ft = hole_in/12; casing_ft = casing_in/12
    return math.pi * (hole_ft**2 - casing_ft**2) / 4

def annulus_hydraulic_diameter_ft(hole_in, casing_in):
    return max(0.0001, (hole_in - casing_in) / 12)

# Load slurry CSV
CSV = "sample_slurries.csv"
if not os.path.exists(CSV):
    st.error("sample_slurries.csv tidak ditemukan — upload ke folder yang sama dengan app.py")
    st.stop()

df = pd.read_csv(CSV)
req_cols = ["name","density_ppg","plastic_viscosity_cP","yield_point_lb100ft2","BHCT_F"]
if not all(c in df.columns for c in req_cols):
    st.error("CSV tidak lengkap. Harus ada kolom: " + ", ".join(req_cols))
    st.stop()

# Sidebar
with st.sidebar:
    st.markdown("<div class='card'><h3>Digital Twin Cementing</h3><p class='muted'>Hybrid Dark v4</p></div>", unsafe_allow_html=True)
    st.markdown("---")

    slurry = st.selectbox("Pilih slurry", df["name"].tolist())
    row = df[df["name"] == slurry].iloc[0]

    hole = st.number_input("Hole diameter (in)", 6.0, 20.0, 8.5)
    casing = st.number_input("Casing OD (in)", 4.0, 16.0, 5.5)
    depth = st.slider("Depth (ft)", 1000, 12000, 3000, 100)
    toc = st.slider("Top of Cement (ft)", 0, depth-50, depth//2)
    rate = st.slider("Pump rate (bbl/min)", 0.5, 18.0, 4.0, 0.1)

    fracture_grad = st.slider("Fracture gradient (ppg)", 12.0, 22.0, 17.0)
    pore_press = st.slider("Pore pressure (ppg)", 9.0, 18.0, 13.5)

    temp = st.number_input("BHCT (°F)", 50, 350, int(row["BHCT_F"]))
    apply_temp = st.checkbox("Apply thermal correction", True)

    show = st.multiselect("Show panels",
        ["ECD","Pressure","Rheology","Schematic","Placement"],
        default=["ECD","Rheology","Schematic"]
    )

# Derived property
density0 = float(row["density_ppg"])
pv0 = float(row["plastic_viscosity_cP"])
yp = float(row["yield_point_lb100ft2"])

density = density_temp_correction(density0, temp) if apply_temp else density0
pv = viscosity_temp_correction(pv0, temp) if apply_temp else pv0

ann_area = annulus_area_ft2(hole, casing)
ann_dh = annulus_hydraulic_diameter_ft(hole, casing)
vol_bbl = ann_area * 7.48052 * (depth - toc) / 42
pump_time = vol_bbl / rate if rate > 0 else 0

# Layout
st.markdown("<div class='card'><h2>Digital Twin Cementing — Hybrid Dark</h2></div>", unsafe_allow_html=True)

col1, col2 = st.columns([1.4, 1])

# =====================================
# ECD PANEL
# =====================================
if "ECD" in show:
    with col1:
        st.markdown("<div class='card'><h4>ECD Profile</h4></div>", unsafe_allow_html=True)

        z = np.linspace(1, depth, 400)
        friction = (pv/10)*(rate/4) + (yp/20)
        geom = max(0.1, 1 + (0.45 - ann_dh))
        friction_psi = friction * z/1000 * 50 * geom
        hydro_psi = 0.052 * density * z
        total_psi = hydro_psi + friction_psi
        ecd = total_psi / (0.052 * z)

        fig, ax = plt.subplots(figsize=(6,5))
        ax.plot(ecd, z, linewidth=2.2, color='#66b2ff', label="ECD")

        # Safe window shading FIXED
        safe_low = np.full_like(z, pore_press)
        safe_high = np.full_like(z, fracture_grad)
        safe_mask = safe_high > safe_low
        ax.fill_betweenx(z, safe_low, safe_high, where=safe_mask, color='#0b5', alpha=0.06)

        ax.axvline(fracture_grad, color='#ff6b6b', linestyle='--')
        ax.axvline(pore_press, color='#66ffb3', linestyle='--')
        ax.invert_yaxis()
        ax.set_xlabel("ECD (ppg)")
        ax.set_ylabel("Depth (ft)")
        ax.grid(ls='--', alpha=0.2)
        st.pyplot(fig)

# PRESSURE PANEL
if "Pressure" in show:
    with col1:
        st.markdown("<div class='card'><h4>Pressure</h4></div>", unsafe_allow_html=True)
        fig2, ax2 = plt.subplots(figsize=(6,3))
        ax2.plot(hydro_psi, z, label="Hydrostatic")
        ax2.plot(friction_psi, z, label="Friction")
        ax2.plot(total_psi, z, label="Total", linewidth=2)
        ax2.invert_yaxis()
        ax2.grid(ls='--', alpha=0.2)
        ax2.legend()
        st.pyplot(fig2)

# =====================================
# RIGHT COLUMN (Rheology + Schematic)
# =====================================
with col2:

    if "Rheology" in show:
        st.markdown("<div class='card'><h4>Rheology</h4></div>", unsafe_allow_html=True)
        sr = np.logspace(0,3,120)
        yp_Pa = yp * 0.4788
        shear = yp_Pa + (pv/1000) * sr
        fig3, ax3 = plt.subplots(figsize=(4,3))
        ax3.loglog(sr, shear)
        ax3.grid(True, which='both', ls='--', alpha=0.2)
        st.pyplot(fig3)

    st.markdown("<div class='card'><h4>Job Summary</h4></div>", unsafe_allow_html=True)
    st.markdown(f"""
    <div class='muted small'>
    Slurry: <b>{slurry}</b><br>
    Density: {density:.2f} ppg<br>
    PV: {pv:.1f} cP<br>
    YP: {yp:.1f}<br>
    Volume: {vol_bbl:.2f} bbl<br>
    Pump time: {pump_time:.1f} min
    </div>
    """, unsafe_allow_html=True)

    if "Schematic" in show:
        st.markdown("<div class='card'><h4>Well Schematic</h4></div>", unsafe_allow_html=True)
        fig4, ax4 = plt.subplots(figsize=(3,8))
        ax4.set_ylim(depth, 0)
        ax4.set_xlim(0,3)
        ax4.fill_betweenx([0,depth], 0.2, 2.8, color='#11151a')
        ax4.fill_betweenx([0,depth], 1.0, 2.0, color='#1f8ea6')
        ax4.fill_betweenx([toc, depth], 0.2, 1.0, color='#ffb46b')
        ax4.fill_betweenx([toc, depth], 2.0, 2.8, color='#ffb46b')
        ax4.axhline(toc, color='yellow')
        ax4.axis('off')
        st.pyplot(fig4)

    if "Placement" in show:
        st.markdown("<div class='card'><h4>Placement Animation</h4></div>", unsafe_allow_html=True)
        t = st.slider("Time (min)", 0.0, pump_time, pump_time/2)
        frac = t/pump_time if pump_time>0 else 0
        front = depth - frac*(depth - toc)
        fig5, ax5 = plt.subplots(figsize=(3,8))
        ax5.set_ylim(depth, 0)
        ax5.set_xlim(0,3)
        ax5.fill_betweenx([0,depth], 0.2, 2.8, color='#11151a')
        ax5.fill_betweenx([0,depth], 1.0, 2.0, color='#1f8ea6')
        ax5.fill_betweenx([front, depth], 0.2, 1.0, color='#ffb46b')
        ax5.fill_betweenx([front, depth], 2.0, 2.8, color='#ffb46b')
        ax5.axhline(front, color='yellow')
        ax5.axis('off')
        st.pyplot(fig5)
