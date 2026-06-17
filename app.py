"""
MedCommand — Hospital Emergency Operations Center v2.0
Professional Streamlit Dashboard

Run:
    streamlit run app.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

from app.config import (
    APP_TITLE, APP_ICON, FOOTER_TEXT, REFRESH_INTERVAL,
    LIGHT, DARK, DOCTOR_ROSTER,
)
from app.state import (
    init_state, advance, get_sim, get_ml, get_logger,
    get_config, get_snapshot, reset_simulation,
)
from app.styles import get_dashboard_css

_FRAGMENT = hasattr(st, "fragment")


# ══════════════════════════════════════════════════════════════════════════════
#  THEME HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def th() -> dict:
    return DARK if get_config().dark_theme else LIGHT


def _plot(height: int = 220, **kw) -> dict:
    """Build a Plotly layout dict. Pass showlegend=True and legend=dict(...) directly in **kw."""
    c = th()
    base = dict(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=c["text"], family="Inter, sans-serif", size=11),
        margin=dict(l=34, r=10, t=18, b=28),
        height=height,
        showlegend=False,
    )
    base.update(kw)
    return base


def _ax(grid: bool = True) -> dict:
    c = th()
    out = dict(tickfont=dict(color=c["tick"], size=10))
    if grid:
        out["gridcolor"] = c["grid"]
    else:
        out["showgrid"] = False
    return out


# ══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════

def render_sidebar() -> None:
    sim = get_sim()
    cfg = get_config()
    snap = get_snapshot()
    c = th()

    with st.sidebar:
        # Logo
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:10px;padding:6px 0 18px">
          <div style="width:34px;height:34px;background:{c['accent']};border-radius:8px;
                       display:flex;align-items:center;justify-content:center;color:white;font-size:18px">⚕</div>
          <div>
            <div style="font-weight:700;font-size:15px;color:{c['accent']}">MedCommand</div>
            <div style="font-size:11px;color:{c['text3']}">Emergency Operations</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        # Sim status badge
        if sim.is_running and not sim.is_paused:
            st.markdown(f'<span style="color:{c["green"]};font-weight:700;font-size:12px">● SIMULATION LIVE</span>', unsafe_allow_html=True)
        elif sim.is_paused:
            st.markdown(f'<span style="color:{c["amber"]};font-weight:700;font-size:12px">⏸ PAUSED</span>', unsafe_allow_html=True)
        else:
            st.markdown(f'<span style="color:{c["text3"]};font-weight:700;font-size:12px">⏹ STOPPED</span>', unsafe_allow_html=True)

        col1, col2, col3 = st.columns([2, 1.4, 1])
        with col1:
            if st.button("▶ Start", use_container_width=True, type="primary",
                         disabled=(sim.is_running and not sim.is_paused)):
                sim.is_running = True
                sim.is_paused  = False
                get_logger().sim("SYSTEM", "Simulation started by operator", sim.tick)
        with col2:
            lbl = "▶ Resume" if sim.is_paused else "⏸ Pause"
            if st.button(lbl, use_container_width=True, disabled=not sim.is_running):
                sim.is_paused = not sim.is_paused
                get_logger().sim("SYSTEM", "Simulation " + ("paused" if sim.is_paused else "resumed"), sim.tick)
        with col3:
            if st.button("↺", use_container_width=True):
                reset_simulation()
                st.rerun()

        st.divider()

        # Configuration
        st.markdown(f'<span style="font-size:11px;font-weight:700;color:{c["text3"]};text-transform:uppercase;letter-spacing:.06em">Configuration</span>', unsafe_allow_html=True)
        new_docs  = st.slider("Doctors on duty", 2, 5, cfg.num_doctors)
        new_rate  = st.slider("Arrival rate", 0.10, 0.80, cfg.arrival_rate, step=0.05, format="%.2f")
        new_speed = st.select_slider("Refresh speed (s)", [1.0, 1.5, 2.0, 2.5, 3.0, 4.0], value=cfg.sim_speed)

        if new_docs != cfg.num_doctors:
            cfg.num_doctors = new_docs
        if abs(new_rate - cfg.arrival_rate) > 0.001:
            cfg.arrival_rate = new_rate
            sim.arrival_rate = new_rate
        cfg.sim_speed = new_speed

        st.divider()

        # Live stats
        st.markdown(f'<span style="font-size:11px;font-weight:700;color:{c["text3"]};text-transform:uppercase;letter-spacing:.06em">Live Stats</span>', unsafe_allow_html=True)
        ca, cb = st.columns(2)
        ca.metric("Queue",    len(snap.queue))
        cb.metric("Served",   snap.patients_served)
        ca.metric("Tick",     snap.tick)
        cb.metric("Incidents",len(snap.incidents))

        st.divider()
        cfg.dark_theme = st.toggle("🌙 Dark theme", value=cfg.dark_theme)

        st.divider()
        st.markdown(f'<span style="font-size:11px;font-weight:700;color:{c["text3"]};text-transform:uppercase;letter-spacing:.06em">Emergency Controls</span>', unsafe_allow_html=True)

        if st.button("🚨 Trigger Mass Casualty Event", use_container_width=True):
            inc = sim.trigger_mass_casualty()
            get_logger().crit("INCIDENT", f"MCE activated — {inc.title}", sim.tick)
            st.toast(f"🚨 MCE: {inc.title}", icon="🚨")
            st.rerun()

        if st.button("⚡ Emergency Patient Surge", use_container_width=True):
            inc = sim.trigger_emergency_spike()
            get_logger().warn("INCIDENT", f"Patient surge — {inc.title}", sim.tick)
            st.toast("⚡ Emergency surge activated", icon="⚡")
            st.rerun()

        if snap.incidents:
            if st.button("✓ Resolve All Incidents", use_container_width=True):
                cnt = sim.resolve_all_incidents()
                get_logger().ok("INCIDENT", f"Operator resolved {cnt} incidents", sim.tick)
                st.toast(f"✓ {cnt} incident(s) resolved")
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE 1 — LIVE OPERATIONS
# ══════════════════════════════════════════════════════════════════════════════

def page_live_ops(snap) -> None:
    snap = get_snapshot()  # always use latest
    c = th()

    # Alerts
    if snap.critical_count > 3:
        st.error(f"🔴 **CRITICAL SURGE** — {snap.critical_count} critical patients in queue. Immediate action required.")
    if len(snap.queue) > 12:
        st.warning(f"⚠️ **Queue overload** — {len(snap.queue)} patients waiting. Consider increasing staff.")
    if snap.incidents:
        st.info(f"🚨 **{len(snap.incidents)} active incident(s)** in progress. See Incident Management tab.")

    # KPIs
    busy_docs = sum(1 for d in snap.doctors if d.status.value in ("Busy", "Emergency Response"))
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Patients in Queue",  len(snap.queue),
               delta="High" if len(snap.queue) > 10 else None,
               delta_color="inverse")
    k2.metric("Active Doctors",     f"{busy_docs}/{len(snap.doctors)}")
    k3.metric("Avg Wait Time",      f"{snap.avg_wait:.0f} min",
               delta="Long" if snap.avg_wait > 20 else None,
               delta_color="inverse")
    k4.metric("Critical Patients",  snap.critical_count,
               delta="Critical" if snap.critical_count > 2 else None,
               delta_color="inverse")

    # Row 1 — trend + feed
    col_trend, col_feed = st.columns([3, 2])

    with col_trend:
        st.markdown(f'<div style="font-size:12px;font-weight:700;color:{c["text3"]};text-transform:uppercase;margin-bottom:6px">Queue & Wait Time Trend</div>', unsafe_allow_html=True)
        if len(snap.history_queue) > 1:
            tks = list(range(1, len(snap.history_queue) + 1))
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=tks, y=snap.history_queue, name="Queue Size",
                                     line=dict(color=c["amber"], width=2),
                                     fill="tozeroy", fillcolor=f"rgba(245,158,11,0.10)"))
            fig.add_trace(go.Scatter(x=tks, y=snap.history_wait, name="Avg Wait (ticks)",
                                     line=dict(color=c["purple"], width=2, dash="dot"),
                                     fill="tozeroy", fillcolor=f"rgba(139,92,246,0.08)"))
            fig.update_layout(**_plot(260,
                                      showlegend=True,
                                      legend=dict(orientation="h", y=1.12, x=0, font=dict(size=10)),
                                      xaxis=dict(showgrid=False, showticklabels=False),
                                      yaxis=_ax()))
            st.plotly_chart(fig, use_container_width=True)

        st.markdown(f'<div style="font-size:12px;font-weight:700;color:{c["text3"]};text-transform:uppercase;margin-bottom:6px">Department Load</div>', unsafe_allow_html=True)
        if snap.dept_load:
            df = pd.DataFrame({"Dept": list(snap.dept_load.keys()),
                                "Patients": list(snap.dept_load.values())})
            colors = [c["red"], c["accent"], c["purple"], c["green"], c["amber"], c["teal"]]
            fig2 = go.Figure(go.Bar(x=df["Dept"], y=df["Patients"],
                                    marker_color=colors, marker=dict(cornerradius=4)))
            fig2.update_layout(**_plot(180,
                                       xaxis=_ax(grid=False),
                                       yaxis=_ax()))
            st.plotly_chart(fig2, use_container_width=True)

    with col_feed:
        # Activity feed
        st.markdown(f'<div style="font-size:12px;font-weight:700;color:{c["text3"]};text-transform:uppercase;margin-bottom:6px">Activity Feed</div>', unsafe_allow_html=True)
        events = list(reversed(get_sim().event_log[-20:]))
        ev_color = {"ARRIVE": c["amber"], "ASSIGN": c["accent"], "DONE": c["green"],
                    "INCIDENT": c["red"], "RESOLVE": c["green"]}
        ev_icon  = {"ARRIVE": "→", "ASSIGN": "🩺", "DONE": "✓", "INCIDENT": "🚨", "RESOLVE": "✅"}
        feed_html = ""
        for ev in events:
            col = ev_color.get(ev["type"], c["text3"])
            ico = ev_icon.get(ev["type"], "•")
            feed_html += f"""
            <div style="display:flex;gap:8px;padding:6px 8px;border-radius:6px;
                         background:{c['surface2']};margin-bottom:4px;
                         border-left:3px solid {col}">
              <span style="color:{c['text3']};white-space:nowrap;font-size:10px;margin-top:1px">{ev['timestamp']}</span>
              <span style="font-size:12px;color:{c['text']}">{ico} {ev['message']}</span>
            </div>"""
        st.markdown(f'<div style="max-height:300px;overflow-y:auto">{feed_html}</div>', unsafe_allow_html=True)

        # Doctor status summary
        st.markdown(f'<div style="font-size:12px;font-weight:700;color:{c["text3"]};text-transform:uppercase;margin:14px 0 6px">Doctor Status ({len(snap.doctors)} on duty)</div>', unsafe_allow_html=True)
        status_info = {
            "Available":          c["green"],
            "Busy":               c["accent"],
            "On Break":           c["amber"],
            "Emergency Response": c["red"],
        }
        doc_html = ""
        for status, color in status_info.items():
            cnt = sum(1 for d in snap.doctors if d.status.value == status)
            doc_html += f"""<div style="display:flex;justify-content:space-between;align-items:center;
                         padding:7px 0;border-bottom:1px solid {c['border']}">
              <span style="font-size:13px"><span style="color:{color}">●</span> {status}</span>
              <strong style="font-size:13px;color:{c['text']}">{cnt}</strong>
            </div>"""
        st.markdown(doc_html, unsafe_allow_html=True)

        # Priority donut
        if snap.queue:
            st.markdown(f'<div style="font-size:12px;font-weight:700;color:{c["text3"]};text-transform:uppercase;margin:14px 0 6px">Queue Priority</div>', unsafe_allow_html=True)
            norm = len(snap.queue) - snap.critical_count - snap.urgent_count
            fig3 = go.Figure(go.Pie(
                labels=["Critical", "Urgent", "Normal"],
                values=[snap.critical_count, snap.urgent_count, max(0, norm)],
                marker_colors=[c["red"], c["amber"], c["accent"]],
                hole=0.55,
                textfont_size=10,
            ))
            fig3.update_layout(**_plot(160,
                                       showlegend=True,
                                       legend=dict(orientation="h", y=-0.15, font=dict(size=10))))
            st.plotly_chart(fig3, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE 2 — QUEUE & DOCTORS
# ══════════════════════════════════════════════════════════════════════════════

def page_queue_doctors(snap) -> None:
    snap = get_snapshot()  # always use latest
    c = th()
    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown(f'<div style="font-size:12px;font-weight:700;color:{c["text3"]};text-transform:uppercase;margin-bottom:10px">👨‍⚕️ Doctor Panel</div>', unsafe_allow_html=True)
        for doc in snap.doctors:
            sc = {"Available": c["green"], "Busy": c["accent"],
                  "On Break": c["amber"], "Emergency Response": c["red"]}.get(doc.status.value, c["text3"])
            patient_txt = f"P{doc.current_patient.pid}: {doc.current_patient.name}" if doc.current_patient else "No patient"
            util_bar = min(100, int(doc.utilization_pct))
            st.markdown(f"""
            <div style="background:{c['surface2']};border:1px solid {c['border']};
                         border-radius:10px;padding:12px 14px;margin-bottom:8px">
              <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">
                <div style="width:38px;height:38px;border-radius:50%;background:{doc.color}22;
                             color:{doc.color};display:flex;align-items:center;justify-content:center;
                             font-weight:700;font-size:13px;flex-shrink:0">{doc.initials}</div>
                <div style="flex:1;min-width:0">
                  <div style="font-weight:600;font-size:13px;color:{c['text']}">{doc.name}</div>
                  <div style="font-size:11px;color:{c['text3']}">{doc.department}</div>
                </div>
                <span style="background:{sc}22;color:{sc};padding:3px 9px;border-radius:12px;
                              font-size:10px;font-weight:700;white-space:nowrap">{doc.status.value}</span>
              </div>
              <div style="font-size:11px;color:{c['text2']};margin-bottom:7px">
                🩺 {patient_txt} &nbsp;|&nbsp; Treated: <strong>{doc.patients_treated}</strong>
              </div>
              <div style="height:5px;background:{c['border']};border-radius:4px;overflow:hidden">
                <div style="width:{util_bar}%;height:100%;background:{doc.color};border-radius:4px;transition:width .6s"></div>
              </div>
              <div style="font-size:10px;color:{c['text3']};margin-top:3px">{doc.utilization_pct:.0f}% utilization</div>
            </div>""", unsafe_allow_html=True)

    with col2:
        st.markdown(f'<div style="font-size:12px;font-weight:700;color:{c["text3"]};text-transform:uppercase;margin-bottom:10px">📋 Patient Queue ({len(snap.queue)} waiting)</div>', unsafe_allow_html=True)
        if not snap.queue:
            st.markdown(f'<div style="color:{c["text3"]};text-align:center;padding:28px;font-size:13px">Queue is empty — no patients waiting</div>', unsafe_allow_html=True)
        else:
            for i, p in enumerate(snap.queue[:20]):
                pc = {"Critical": c["red"], "Urgent": c["amber"], "Normal": c["accent"]}.get(p.priority.value, c["text3"])
                pbg = {"Critical": f"{c['red']}12", "Urgent": f"{c['amber']}12", "Normal": f"{c['surface2']}"}.get(p.priority.value, c["surface2"])
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:10px;padding:8px 10px;
                             border-radius:8px;border-left:4px solid {pc};background:{pbg};margin-bottom:5px">
                  <div style="width:24px;height:24px;border-radius:50%;background:{c['surface']};
                               display:flex;align-items:center;justify-content:center;
                               font-size:10px;font-weight:700;color:{c['text2']};flex-shrink:0">{i+1}</div>
                  <div style="flex:1;min-width:0">
                    <div style="font-weight:600;font-size:13px;color:{c['text']}">P{p.pid} {p.name}</div>
                    <div style="font-size:11px;color:{c['text3']}">{p.department}</div>
                  </div>
                  <div style="text-align:right">
                    <div style="background:{pc}22;color:{pc};padding:2px 9px;border-radius:10px;
                                 font-size:10px;font-weight:700;margin-bottom:2px">{p.priority.value}</div>
                    <div style="font-size:10px;color:{c['text3']}">{p.wait_ticks}t wait · Est {p.estimated_wait}m</div>
                  </div>
                </div>""", unsafe_allow_html=True)

    # Doctor performance chart
    st.markdown(f'<div style="font-size:12px;font-weight:700;color:{c["text3"]};text-transform:uppercase;margin:16px 0 8px">Doctor Performance</div>', unsafe_allow_html=True)
    df = pd.DataFrame({
        "Doctor":    [d.name.replace("Dr. ", "") for d in snap.doctors],
        "Treated":   [d.patients_treated for d in snap.doctors],
        "Util %":    [d.utilization_pct for d in snap.doctors],
    })
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Patients Treated", x=df["Doctor"], y=df["Treated"],
                         marker_color=[d.color for d in snap.doctors],
                         marker=dict(cornerradius=4)))
    fig.add_trace(go.Scatter(name="Utilization %", x=df["Doctor"], y=df["Util %"],
                              mode="lines+markers", yaxis="y2",
                              line=dict(color=c["purple"], width=2),
                              marker=dict(size=7, color=c["purple"])))
    fig.update_layout(**_plot(220,
                               showlegend=True,
                               legend=dict(orientation="h", y=1.12, x=0, font=dict(size=10)),
                               xaxis=_ax(grid=False),
                               yaxis=_ax(),
                               yaxis2=dict(overlaying="y", side="right", showgrid=False,
                                           tickfont=dict(color=c["tick"], size=10),
                                           range=[0, 105])))
    st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE 3 — ML PREDICTIONS
# ══════════════════════════════════════════════════════════════════════════════

def page_ml(snap) -> None:
    snap = get_snapshot()  # always use latest
    c = th()
    ml = get_ml()
    cfg = get_config()

    if not ml.is_ready:
        st.info("🤖 ML models initializing — simulation must run at least one full cycle (8 ticks).")
        return

    models = ml.models

    # Model cards
    m_cols = st.columns(3)
    mk_info = [
        ("rf",  "Random Forest",   c["accent"],  "badge-blue"),
        ("xg",  "XGBoost",         c["green"],   "badge-green"),
        ("dt",  "Decision Tree",   c["purple"],  "badge-purple"),
    ]
    for col, (key, name, bar_col, _) in zip(m_cols, mk_info):
        with col:
            if key not in models:
                continue
            m = models[key]
            bc = c["green"] if m.is_best else c["text3"]
            bt = "★ Best Model" if m.is_best else m.badge
            r2p = int(m.r2 * 100)
            st.markdown(f"""
            <div style="background:{c['surface2']};border:1px solid {c['border']};
                         border-radius:10px;padding:16px;border-top:3px solid {bar_col}">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
                <div style="font-weight:700;font-size:14px;color:{c['text']}">{name}</div>
                <span style="background:{bc}22;color:{bc};padding:3px 9px;border-radius:12px;
                              font-size:11px;font-weight:700">{bt}</span>
              </div>
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px">
                <div>
                  <div style="font-size:10px;color:{c['text3']};text-transform:uppercase;letter-spacing:.05em">RMSE</div>
                  <div style="font-weight:700;font-size:16px;color:{c['text']}">{m.rmse}</div>
                </div>
                <div>
                  <div style="font-size:10px;color:{c['text3']};text-transform:uppercase;letter-spacing:.05em">R²</div>
                  <div style="font-weight:700;font-size:16px;color:{c['text']}">{m.r2:.3f}</div>
                </div>
                <div>
                  <div style="font-size:10px;color:{c['text3']};text-transform:uppercase;letter-spacing:.05em">MAE</div>
                  <div style="font-weight:700;font-size:16px;color:{c['text']}">{m.mae}</div>
                </div>
                <div>
                  <div style="font-size:10px;color:{c['text3']};text-transform:uppercase;letter-spacing:.05em">Accuracy</div>
                  <div style="font-weight:700;font-size:16px;color:{c['text']}">{m.accuracy_pct:.1f}%</div>
                </div>
              </div>
              <div style="height:8px;background:{c['border']};border-radius:4px;overflow:hidden">
                <div style="width:{r2p}%;height:100%;background:{bar_col};border-radius:4px;transition:width 1s"></div>
              </div>
              <div style="font-size:10px;color:{c['text3']};margin-top:4px">Trained at tick {m.trained_at_tick}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("")
    col_pred, col_fi = st.columns(2)

    with col_pred:
        st.markdown(f'<div style="font-size:12px;font-weight:700;color:{c["text3"]};text-transform:uppercase;margin-bottom:10px">🎯 Live Wait Time Prediction</div>', unsafe_allow_html=True)
        busy = sum(1 for d in snap.doctors if d.status.value in ("Busy", "Emergency Response"))

        for prio in ["Critical", "Urgent", "Normal"]:
            prio_int = {"Critical": 0, "Urgent": 1, "Normal": 2}[prio]
            preds = ml.predict_wait(len(snap.queue), prio, busy, cfg.arrival_rate)
            avg_p = sum(preds.values()) // max(1, len(preds))
            spread = max(preds.values()) - min(preds.values()) if len(preds) > 1 else 0
            pc = {"Critical": c["red"], "Urgent": c["amber"], "Normal": c["accent"]}[prio]
            st.markdown(f"""
            <div style="display:flex;justify-content:space-between;align-items:center;
                         padding:10px 0;border-bottom:1px solid {c['border']}">
              <span style="background:{pc}22;color:{pc};padding:3px 10px;border-radius:12px;
                            font-size:11px;font-weight:700">{prio}</span>
              <span style="font-weight:700;font-size:20px;color:{c['text']}">{avg_p} min</span>
              <span style="font-size:11px;color:{c['text3']}">±{spread} min spread</span>
            </div>""", unsafe_allow_html=True)

        best_m = next((models[k] for k in models if models[k].is_best), None)
        if best_m:
            st.markdown(f"""
            <div style="margin-top:14px;padding:10px 12px;background:{c['accent']}15;
                         border-radius:8px;font-size:12px;color:{c['accent']}">
              <strong>Active model:</strong> {ml.best_model_name}
              &nbsp;|&nbsp; R²: {best_m.r2:.3f}
              &nbsp;|&nbsp; Retrains: {ml.retrain_count}
            </div>""", unsafe_allow_html=True)

    with col_fi:
        st.markdown(f'<div style="font-size:12px;font-weight:700;color:{c["text3"]};text-transform:uppercase;margin-bottom:10px">📊 Feature Importance</div>', unsafe_allow_html=True)
        if ml.feature_importance:
            fi = ml.feature_importance.normalized()
            df_fi = pd.DataFrame({"Feature": list(fi.keys()), "Importance": list(fi.values())})
            df_fi = df_fi.sort_values("Importance", ascending=True)
            fig = go.Figure(go.Bar(
                x=df_fi["Importance"], y=df_fi["Feature"],
                orientation="h",
                marker=dict(color=c["accent"], cornerradius=4),
                text=[f"{v:.1%}" for v in df_fi["Importance"]],
                textposition="outside",
                textfont=dict(size=10, color=c["tick"]),
            ))
            fig.update_layout(**_plot(220,
                                      xaxis=dict(tickformat=".0%", gridcolor=c["grid"], tickfont=dict(color=c["tick"], size=10), range=[0, max(fi.values()) * 1.3]),
                                      yaxis=dict(tickfont=dict(color=c["tick"], size=10), showgrid=False)))
            st.plotly_chart(fig, use_container_width=True)

    # Model history chart
    st.markdown(f'<div style="font-size:12px;font-weight:700;color:{c["text3"]};text-transform:uppercase;margin-bottom:8px">📈 Model Accuracy History (R²)</div>', unsafe_allow_html=True)
    h = ml.history
    if h.get("rf"):
        tks = list(range(1, len(h["rf"]) + 1))
        fig = go.Figure()
        series = [("rf", "Random Forest", c["accent"]),
                  ("xg", "XGBoost",       c["green"]),
                  ("dt", "Decision Tree", c["purple"])]
        dashes = ["solid", "solid", "dot"]
        for (key, name, col_), dash in zip(series, dashes):
            if h.get(key):
                fig.add_trace(go.Scatter(x=tks, y=h[key][:len(tks)], name=name,
                                          line=dict(color=col_, width=2, dash=dash),
                                          mode="lines+markers", marker=dict(size=5)))
        fig.add_hline(y=0.8, line_dash="dot", line_color=c["amber"],
                      annotation_text="0.80 threshold", annotation_font_size=9)
        fig.update_layout(**_plot(220,
                                   showlegend=True,
                                   legend=dict(orientation="h", y=1.12, x=0, font=dict(size=10)),
                                   yaxis=dict(range=[0.35, 1.02], gridcolor=c["grid"],
                                              tickfont=dict(color=c["tick"]), tickformat=".2f"),
                                   xaxis=dict(showgrid=False, tickfont=dict(color=c["tick"]))))
        st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE 4 — RESOURCE UTILIZATION
# ══════════════════════════════════════════════════════════════════════════════

def page_resources(snap) -> None:
    snap = get_snapshot()  # always use latest
    c = th()
    busy = sum(1 for d in snap.doctors if d.status.value in ("Busy", "Emergency Response"))
    util = snap.doctor_utilization
    load = min(100, int(snap.bed_occupancy * 0.4 + util * 0.6))

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Bed Occupancy",     f"{snap.bed_occupancy:.0f}%")
    k2.metric("Doctor Utilization",f"{util:.0f}%")
    k3.metric("Throughput / hr",   f"{snap.throughput_per_hour:.1f}")
    k4.metric("System Load",       f"{load}%",
               delta="Overloaded" if load > 85 else None, delta_color="inverse")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f'<div style="font-size:12px;font-weight:700;color:{c["text3"]};text-transform:uppercase;margin-bottom:10px">🕐 Peak Hours Heatmap</div>', unsafe_allow_html=True)
        hours = snap.peak_hours
        mx = max(hours) if any(hours) else 1
        hmap = ""
        for h in range(0, 24, 6):
            hmap += f'<div style="display:flex;gap:3px;margin-bottom:4px;align-items:center">'
            hmap += f'<span style="font-size:10px;color:{c["text3"]};width:42px">{h:02d}:00</span>'
            for i in range(6):
                idx = h + i
                val = hours[idx] if idx < 24 else 0
                pct = val / mx if mx > 0 else 0
                bg = c["red"] if pct > 0.7 else c["amber"] if pct > 0.4 else c["teal"]
                opacity = 0.18 + 0.82 * pct
                hmap += f'<div style="flex:1;height:28px;background:{bg};opacity:{opacity:.2f};border-radius:4px;display:flex;align-items:center;justify-content:center;font-size:9px;color:white;font-weight:700">{val}</div>'
            hmap += f'<span style="font-size:9px;color:{c["text3"]};width:42px;padding-left:4px">{(h+5):02d}:59</span>'
            hmap += "</div>"
        st.markdown(hmap, unsafe_allow_html=True)

    with col2:
        st.markdown(f'<div style="font-size:12px;font-weight:700;color:{c["text3"]};text-transform:uppercase;margin-bottom:10px">📊 Department Workload</div>', unsafe_allow_html=True)
        from app.config import DEPARTMENTS
        df = pd.DataFrame({
            "Dept": DEPARTMENTS,
            "Patients": [snap.dept_load.get(d, 0) for d in DEPARTMENTS],
        })
        colors = [c["red"], c["accent"], c["purple"], c["green"], c["amber"], c["teal"]]
        fig = go.Figure(go.Bar(x=df["Dept"], y=df["Patients"],
                               marker_color=colors, marker=dict(cornerradius=4)))
        fig.update_layout(**_plot(220, xaxis=_ax(grid=False), yaxis=_ax()))
        st.plotly_chart(fig, use_container_width=True)

    # Utilization timeline
    st.markdown(f'<div style="font-size:12px;font-weight:700;color:{c["text3"]};text-transform:uppercase;margin-bottom:8px">⚡ Doctor Utilization Timeline</div>', unsafe_allow_html=True)
    if snap.history_utilization:
        tks = list(range(1, len(snap.history_utilization) + 1))
        fig2 = go.Figure()
        fill_accent = "rgba(56,189,248,0.12)" if get_config().dark_theme else "rgba(14,165,233,0.12)"
        fig2.add_trace(go.Scatter(x=tks, y=snap.history_utilization, name="Utilization %",
                                   line=dict(color=c["accent"], width=2),
                                   fill="tozeroy", fillcolor=fill_accent))
        fig2.add_hline(y=80, line_dash="dot", line_color=c["amber"],
                       annotation_text="80% threshold", annotation_font_size=9)
        fig2.add_hline(y=95, line_dash="dot", line_color=c["red"],
                       annotation_text="95% critical", annotation_font_size=9)
        fig2.update_layout(**_plot(190,
                                    yaxis=dict(range=[0, 110], gridcolor=c["grid"],
                                               tickfont=dict(color=c["tick"])),
                                    xaxis=dict(showgrid=False, showticklabels=False)))
        st.plotly_chart(fig2, use_container_width=True)

    # Per-doctor utilization bars
    st.markdown(f'<div style="font-size:12px;font-weight:700;color:{c["text3"]};text-transform:uppercase;margin-bottom:10px">Doctor Efficiency Breakdown</div>', unsafe_allow_html=True)
    for doc in snap.doctors:
        u = min(100, doc.utilization_pct)
        color = c["red"] if u > 90 else c["amber"] if u > 70 else c["green"]
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:7px">
          <span style="width:110px;font-size:12px;color:{c['text']};font-weight:500">{doc.name.replace('Dr. ','')}</span>
          <div style="flex:1;height:8px;background:{c['border']};border-radius:4px;overflow:hidden">
            <div style="width:{u:.0f}%;height:100%;background:{color};border-radius:4px;transition:width .6s"></div>
          </div>
          <span style="width:42px;text-align:right;font-size:12px;color:{c['text2']};font-weight:600">{u:.0f}%</span>
        </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE 5 — INCIDENT MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

def page_incidents(snap) -> None:
    snap = get_snapshot()  # always use latest
    c = th()
    surge = "CRITICAL" if len(snap.incidents) > 2 else "Elevated" if snap.incidents else "Normal"
    surge_c = c["red"] if surge == "CRITICAL" else c["amber"] if surge == "Elevated" else c["green"]

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Active Incidents", len(snap.incidents))
    k2.metric("Surge Level",      surge)
    k3.metric("Critical in Queue",snap.critical_count)
    k4.metric("Resolved (session)", snap.patients_served // max(1, snap.tick // 10))

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown(f'<div style="font-size:12px;font-weight:700;color:{c["text3"]};text-transform:uppercase;margin-bottom:10px">🚨 Active Incidents</div>', unsafe_allow_html=True)
        if not snap.incidents:
            st.markdown(f'<div style="color:{c["text3"]};text-align:center;padding:28px;font-size:13px">No active incidents. System normal.</div>', unsafe_allow_html=True)
        else:
            for inc in snap.incidents:
                sev_c = c["red"] if inc.severity == "CRITICAL" else c["amber"] if inc.severity == "HIGH" else c["accent"]
                dur = snap.tick - inc.created_tick
                auto = inc.auto_resolve_after - dur
                st.markdown(f"""
                <div style="background:{c['surface2']};border:1px solid {sev_c}44;
                             border-left:4px solid {sev_c};border-radius:10px;padding:14px;margin-bottom:8px">
                  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px">
                    <strong style="font-size:13px;color:{c['text']}">{inc.title}</strong>
                    <span style="background:{sev_c}22;color:{sev_c};padding:3px 9px;border-radius:12px;
                                  font-size:10px;font-weight:700;flex-shrink:0;margin-left:8px">{inc.severity}</span>
                  </div>
                  <div style="font-size:12px;color:{c['text2']};margin-bottom:6px">{inc.description}</div>
                  <div style="font-size:11px;color:{c['text3']}">
                    Started tick {inc.created_tick} &nbsp;|&nbsp; Duration: {dur} ticks
                    &nbsp;|&nbsp; Auto-resolve in: ~{max(0, auto)} ticks
                  </div>
                </div>""", unsafe_allow_html=True)

        st.markdown("")
        btn1, btn2, btn3 = st.columns(3)
        with btn1:
            if st.button("🚨 Trigger MCE", use_container_width=True, type="primary"):
                inc = get_sim().trigger_mass_casualty()
                get_logger().crit("INCIDENT", f"MCE: {inc.title}", snap.tick)
                st.rerun()
        with btn2:
            if st.button("⚡ Surge", use_container_width=True):
                inc = get_sim().trigger_emergency_spike()
                get_logger().warn("INCIDENT", f"Surge: {inc.title}", snap.tick)
                st.rerun()
        with btn3:
            if st.button("✓ Resolve All", use_container_width=True):
                cnt = get_sim().resolve_all_incidents()
                get_logger().ok("INCIDENT", f"Resolved {cnt} incidents", snap.tick)
                st.rerun()

    with col2:
        st.markdown(f'<div style="font-size:12px;font-weight:700;color:{c["text3"]};text-transform:uppercase;margin-bottom:10px">📈 Incident Timeline</div>', unsafe_allow_html=True)
        if snap.history_incidents:
            fig = go.Figure(go.Bar(
                x=list(range(len(snap.history_incidents))),
                y=snap.history_incidents,
                marker_color=c["red"], opacity=0.75,
                marker=dict(cornerradius=2),
            ))
            fig.update_layout(**_plot(200,
                                       xaxis=dict(showgrid=False, showticklabels=False),
                                       yaxis=dict(gridcolor=c["grid"], tickfont=dict(color=c["tick"]),
                                                  dtick=1)))
            st.plotly_chart(fig, use_container_width=True)

        st.markdown(f'<div style="font-size:12px;font-weight:700;color:{c["text3"]};text-transform:uppercase;margin:14px 0 10px">Critical vs Urgent Trend</div>', unsafe_allow_html=True)
        if snap.history_critical:
            tks = list(range(1, len(snap.history_critical) + 1))
            fig2 = go.Figure()
            fill_red = "rgba(248,113,113,0.12)" if get_config().dark_theme else "rgba(239,68,68,0.12)"
            fig2.add_trace(go.Scatter(x=tks, y=snap.history_critical, name="Critical",
                                       line=dict(color=c["red"], width=2),
                                       fill="tozeroy", fillcolor=fill_red))
            fig2.update_layout(**_plot(180,
                                        showlegend=True,
                                        legend=dict(orientation="h", y=1.12, x=0, font=dict(size=10)),
                                        xaxis=dict(showgrid=False, showticklabels=False),
                                        yaxis=dict(gridcolor=c["grid"], tickfont=dict(color=c["tick"]),
                                                   dtick=1, range=[0, max(snap.history_critical or [0]) + 2])))
            st.plotly_chart(fig2, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE 6 — DATABASE & AUDIT LOGS
# ══════════════════════════════════════════════════════════════════════════════

def page_database(snap) -> None:
    snap = get_snapshot()  # always use latest
    c = th()
    logger = get_logger()
    stats  = logger.stats()

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Events",   stats["total"])
    k2.metric("Patient Events", stats["info"])
    k3.metric("ML Events",      stats["ml"])
    k4.metric("Warnings",       stats["warn"] + stats["crit"])

    # Filter bar
    fc1, fc2, fc3, fc4, fc5 = st.columns([3, 1.5, 1.8, 1.2, 1])
    with fc1:
        search = st.text_input("Search", placeholder="Filter messages…", label_visibility="collapsed")
    with fc2:
        level_f = st.selectbox("Level", ["", "INFO", "WARN", "CRIT", "ML", "SIM", "OK"],
                                label_visibility="collapsed")
    with fc3:
        cat_options = [""] + logger.get_all_categories()
        cat_f = st.selectbox("Category", cat_options, label_visibility="collapsed")
    with fc4:
        sort_sel = st.selectbox("Sort", ["Newest first", "Oldest first"],
                                 label_visibility="collapsed")
    with fc5:
        if st.button("🗑 Clear", use_container_width=True):
            logger.clear()
            st.rerun()

    entries = logger.filter(
        search=search,
        level=level_f,
        category=cat_f,
        sort_desc=(sort_sel == "Newest first"),
        limit=300,
    )

    if not entries:
        st.info("No log entries match the current filter.")
        return

    level_style = {
        "INFO": (c["accent"],  f"{c['accent']}18"),
        "WARN": (c["amber"],   f"{c['amber']}18"),
        "CRIT": (c["red"],     f"{c['red']}18"),
        "ML":   (c["purple"],  f"{c['purple']}18"),
        "SIM":  (c["teal"],    f"{c['teal']}18"),
        "OK":   (c["green"],   f"{c['green']}18"),
    }

    rows_html = ""
    for entry in entries[:250]:
        lc, lbg = level_style.get(entry.level, (c["text3"], c["surface2"]))
        rows_html += f"""
        <div style="display:flex;align-items:flex-start;gap:10px;padding:7px 0;
                     border-bottom:1px solid {c['border']};font-size:12px">
          <span style="font-family:'JetBrains Mono',monospace;color:{c['text3']};
                        width:62px;flex-shrink:0;font-size:11px">{entry.timestamp}</span>
          <span style="background:{lbg};color:{lc};padding:2px 8px;border-radius:8px;
                        font-size:10px;font-weight:700;flex-shrink:0;height:fit-content;
                        white-space:nowrap">{entry.level}</span>
          <span style="color:{c['text3']};width:76px;flex-shrink:0;font-size:11px">{entry.category}</span>
          <span style="color:{c['text']};flex:1">{entry.message}</span>
        </div>"""

    # --- FIXED SECTION ---
    # HTML block ko single line configuration me convert kiya hai taake markdown formatting mess up na ho
    container_html = f'<div style="max-height:500px;overflow-y:auto;background:{c["surface"]};border:1px solid {c["border"]};border-radius:10px;padding:12px 16px">{rows_html}</div>'
    st.markdown(container_html, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  AUTO-REFRESH FRAGMENT
# ══════════════════════════════════════════════════════════════════════════════

if _FRAGMENT:
    @st.fragment(run_every=REFRESH_INTERVAL)
    def _auto_tick() -> None:
        sim = get_sim()
        cfg = get_config()
        if sim.is_running and not sim.is_paused:
            advance(ticks=cfg.ticks_per_refresh)
else:
    def _auto_tick() -> None:
        sim = get_sim()
        cfg = get_config()
        if sim.is_running and not sim.is_paused:
            advance(ticks=cfg.ticks_per_refresh)


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon=APP_ICON,
        layout="wide",
        initial_sidebar_state="expanded",
    )

    init_state()
    cfg  = get_config()
    sim  = get_sim()
    snap = get_snapshot()

    st.markdown(get_dashboard_css(dark=cfg.dark_theme), unsafe_allow_html=True)

    # Header bar
    c = th()
    run_state = "🟢 LIVE" if (sim.is_running and not sim.is_paused) else ("⏸ PAUSED" if sim.is_paused else "⏹ STOPPED")
    run_color = c["green"] if (sim.is_running and not sim.is_paused) else (c["amber"] if sim.is_paused else c["text3"])
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:14px;padding:8px 0 18px;
                 border-bottom:1px solid {c['border']};margin-bottom:18px">
      <div style="width:34px;height:34px;background:{c['accent']};border-radius:8px;
                   display:flex;align-items:center;justify-content:center;color:white;font-size:18px">⚕</div>
      <div>
        <div style="font-weight:700;font-size:16px;color:{c['accent']}">MedCommand</div>
        <div style="font-size:11px;color:{c['text3']}">Hospital Emergency Operations Center</div>
      </div>
      <div style="flex:1"></div>
      <span style="color:{run_color};font-weight:700;font-size:13px">{run_state}</span>
      <span style="font-size:12px;color:{c['text3']}">Tick {snap.tick}</span>
      <span style="font-size:12px;color:{c['text3']}">v2.0</span>
    </div>""", unsafe_allow_html=True)

    render_sidebar()

    snap = get_snapshot()   # re-fetch after sidebar may have advanced it

    tabs = st.tabs([
        "📡 Live Operations",
        "🏥 Queue & Doctors",
        "🤖 ML Predictions",
        "📊 Resource Center",
        "🚨 Incident Mgmt",
        "🗄 Database Logs",
    ])

    with tabs[0]: page_live_ops(snap)
    with tabs[1]: page_queue_doctors(snap)
    with tabs[2]: page_ml(snap)
    with tabs[3]: page_resources(snap)
    with tabs[4]: page_incidents(snap)
    with tabs[5]: page_database(snap)

    st.markdown(f'<div style="text-align:center;padding:14px;font-size:11px;color:{c["text3"]};border-top:1px solid {c["border"]};margin-top:24px">{FOOTER_TEXT}</div>',
                unsafe_allow_html=True)

    # Auto-refresh
    _auto_tick()

    if not _FRAGMENT and sim.is_running and not sim.is_paused:
        time.sleep(cfg.sim_speed)
        st.rerun()


if __name__ == "__main__":
    main()
