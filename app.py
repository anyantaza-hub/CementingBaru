import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import math, os, io

# Page config
st.set_page_config(page_title="Digital Twin Cementing — Level 4 Final", layout="wide")

# Load logo
LOGO = "dtc_logo.svg"
if os.path.exists(LOGO):
    st.sidebar.image(LOGO, width=110)

# Theme: slow gradient shift (implemented via CSS background)
st.markdown("""
<style>
:root{--bg1:#071018;--bg2:#0b1220;--card:#0f1724;--muted:#9fb7c8;--text:#e6eef6;--accent:#4CB3FF}
html, body, [class*="css"] {background: linear-gradient(120deg,var(--bg1),var(--bg2)); color:var(--text);}
.block-container{padding:24px;}
.card { background: rgba(15,23,36,0.6); padding:12px; border-radius:10px; box-shadow: 0 8px 24px rgba(0,0,0,0.6); }
h1, h2, h3 { color: var(--text); }
#MainMenu, header, footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='card'><h1>Digital Twin Cementing — Level 4 Final</h1><p style='color:var(--muted)'>Premium hybrid UI • Dark matte charts (engineering colors) • Circular badge logo</p></div>", unsafe_allow_html=True)

# CSV expected
CSV = "sample_slurries.csv"
if not os.path.exists(CSV):
    st.error(f"CSV file '{CSV}' not found. Upload to repo root.")
    st.stop()

df = pd.read_csv(CSV)
required = ["name","density_ppg","plastic_viscosity_cP","yield_point_lb100ft2","BHCT_F"]
if not all(c in df.columns for c in required):
    st.error("CSV missing required columns. Use provided template.")
    st.stop()

# Sidebar controls
with st.sidebar:
    st.markdown("<div class='card'><h3>Controls</h3></div>", unsafe_allow_html=True)
    slurry = st.selectbox("Slurry", df["name"].tolist())
    row = df[df["name"]==slurry].iloc[0]
    TD = st.number_input("Total Depth TD (ft)", 1000, 20000, 3000, step=100)
    TOC = st.number_input("Top of Cement TOC (ft)", 0, TD-50, int(TD*0.5), step=10)
    hole = st.number_input("Hole diameter (in)", 6.0, 20.0, 8.5, 0.1)
    casing = st.number_input("Casing OD (in)", 4.0, 16.0, 5.5, 0.1)
    rate = st.slider("Pump rate (bbl/min)", 0.5, 20.0, 4.0, 0.1)
    fracture_grad = st.slider("Fracture gradient (ppg)", 12.0, 22.0, 17.0, 0.1)
    pore_press = st.slider("Pore pressure (ppg)", 9.0, 18.0, 13.5, 0.1)
    BHCT = st.number_input("BHCT (°F)", 50, 350, int(row.get("BHCT_F",150)))
    apply_temp = st.checkbox("Apply thermal correction", True)
    st.markdown("---")
    st.markdown("<div style='color:var(--muted)'>Charts use dark-matte theme with traditional blue/green engineering lines for readability on dark backgrounds.</div>", unsafe_allow_html=True)

# Derived properties
def density_temp(ppg, T, T_ref=150.0):
    rho_ref = ppg * 7.48052
    alpha = 0.00028
    rho = rho_ref * (1 - alpha * (T - T_ref))
    return rho / 7.48052

def viscosity_temp(pv, T, T_ref=150.0):
    return max(0.001, pv * np.exp(-0.015*(T-T_ref)))

density0 = float(row["density_ppg"]); pv0 = float(row["plastic_viscosity_cP"]); yp0 = float(row["yield_point_lb100ft2"])
density = density_temp(density0, BHCT) if apply_temp else density0
pv = viscosity_temp(pv0, BHCT) if apply_temp else pv0
yp = yp0

# Geometry
ann_area = math.pi * ((hole/12.0)**2 - (casing/12.0)**2) / 4.0
ann_vol_bbl = ann_area * 7.48052 * (TD - TOC) / 42.0
pump_time = ann_vol_bbl / rate if rate>0 else 0.0

# Main layout
col_left, col_right = st.columns([2,1])

with col_left:
    st.markdown("<div class='card'><h3>ECD Profile (Literature)</h3></div>", unsafe_allow_html=True)

    z = np.linspace(1, TD, 600)
    geom_factor = max(0.1, 1 + (0.45 - max(0.0001, (hole-casing)/12.0)))
    friction = (pv/10.0)*(rate/4.0) + (yp/20.0)
    friction_psi = friction * z/1000.0 * 50.0 * geom_factor
    hydro_psi = 0.052 * density * z
    total_psi = hydro_psi + friction_psi
    ecd = total_psi / (0.052 * z)

    # Dark matte chart: traditional engineering colors (blue/green)
    fig, ax = plt.subplots(figsize=(7,6), facecolor='#0b1220')
    fig.patch.set_facecolor('#0b1220')
    ax.set_facecolor('#0b1220')
    ax.plot(ecd, z, color='#2aa1bf', lw=2.5, label='ECD (total)')  # cyan-green
    ax.plot([fracture_grad]*2, [0, TD], color='#ff6b6b', ls='--', label='Fracture grad')
    # Safe window shading (convert scalars to arrays)
safe_low = np.full_like(z, pore_press)
safe_high = np.full_like(z, fracture_grad)
safe_mask = safe_high > safe_low
ax.fill_betweenx(z, safe_low, safe_high, where=safe_mask, color='#0b5', alpha=0.06)
    ax.fill_betweenx(z, pore_press, fracture_grad, where=(fracture_grad>pore_press), color='#0b5', alpha=0.06)
    ax.invert_yaxis()
    ax.set_xlabel('ECD (ppg)', color='#cfefff')
    ax.set_ylabel('Depth (ft)', color='#cfefff')
    ax.tick_params(colors='#9fb7c8')
    ax.grid(ls='--', alpha=0.18)
    ax.legend(facecolor='#071018', framealpha=0.9)
    st.pyplot(fig)

    # Export button for chart
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', facecolor=fig.get_facecolor())
    buf.seek(0)
    st.download_button("📥 Export ECD Chart (PNG)", data=buf, file_name="ecd_chart.png", mime="image/png")

    st.markdown("<div class='card'><h3>Pressure Components</h3></div>", unsafe_allow_html=True)
    fig2, ax2 = plt.subplots(figsize=(7,2.6), facecolor='#0b1220')
    ax2.set_facecolor('#0b1220')
    ax2.plot(hydro_psi, z, label='Hydrostatic', color='#b6e1ff', lw=1.6)
    ax2.plot(friction_psi, z, label='Friction', color='#ffcf7a', lw=1.6)
    ax2.plot(total_psi, z, label='Total', color='#69b6ff', lw=2)
    ax2.invert_yaxis(); ax2.set_xlabel('Pressure (psi)'); ax2.set_ylabel('Depth (ft)')
    ax2.tick_params(colors='#9fb7c8'); ax2.grid(ls='--', alpha=0.16); ax2.legend(facecolor='#071018')
    st.pyplot(fig2)

with col_right:
    st.markdown("<div class='card'><h3>Job Summary</h3></div>", unsafe_allow_html=True)
    st.markdown(f"""
    <div style='color:#9fb7c8'>
    <b>Slurry</b>: {slurry}<br>
    <b>Density</b>: {density:.2f} ppg<br>
    <b>PV</b>: {pv:.1f} cP<br>
    <b>YP</b>: {yp:.1f} lb/100ft²<br>
    <b>Annulus vol</b>: {ann_vol_bbl:.2f} bbl<br>
    <b>Pump time</b>: {pump_time:.1f} min<br>
    <b>TOC</b>: {TOC} ft
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div class='card'><h3>Well Schematic</h3></div>", unsafe_allow_html=True)
    fig3, ax3 = plt.subplots(figsize=(3,6), facecolor='#0b1220')
    ax3.set_facecolor('#0b1220'); ax3.set_ylim(TD, 0); ax3.set_xlim(0,3)
    ax3.fill_betweenx([0, TD], 0.2, 2.8, color='#081018')
    ax3.fill_betweenx([0, TD], 1.0, 2.0, color='#2aa1bf')
    ax3.fill_betweenx([TOC, TD], 0.2, 1.0, color='#ffb46b', alpha=0.95)
    ax3.fill_betweenx([TOC, TD], 2.0, 2.8, color='#ffb46b', alpha=0.95)
    ax3.axhline(TOC, color='#ffd580', ls='--'); ax3.text(2.9, TOC, f'TOC {int(TOC)} ft', color='white'); ax3.axis('off')
    st.pyplot(fig3)

    if pump_time>0:
        st.markdown("<div class='card'><h3>Placement Simulation</h3></div>", unsafe_allow_html=True)
        t = st.slider("Simulated pump time (min)", 0.0, max(1.0,pump_time*1.2), value=min(pump_time, pump_time*0.4))
        frac = min(1.0, t/pump_time) if pump_time>0 else 0.0
        front = TD - frac*(TD - TOC)
        fig4, ax4 = plt.subplots(figsize=(3,6), facecolor='#0b1220')
        ax4.set_facecolor('#0b1220'); ax4.set_ylim(TD, 0); ax4.set_xlim(0,3)
        ax4.fill_betweenx([0, TD], 0.2, 2.8, color='#081018')
        ax4.fill_betweenx([0, TD], 1.0, 2.0, color='#2aa1bf')
        ax4.fill_betweenx([front, TD], 0.2, 1.0, color='#ffb46b', alpha=0.95)
        ax4.fill_betweenx([front, TD], 2.0, 2.8, color='#ffb46b', alpha=0.95)
        ax4.axhline(front, color='#ffd580', ls='--'); ax4.text(2.9, front, f'Front @{int(front)} ft', color='white'); ax4.axis('off')
        st.pyplot(fig4)

st.markdown("---")
st.markdown("<div style='color:#9fb7c8; font-size:0.9rem'>Level 4 Final — premium UI. For thesis/demo use only; validate with lab/field data for operational work.</div>", unsafe_allow_html=True)
