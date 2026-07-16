"""Generate a synthetic Formula-Student / SAE-SUPRA-style datalogger CSV.

SAMPLE data that *resembles* a student formula car's telemetry, built with real
physics so it passes the /import/validate gate:
  * a CLOSED circuit centreline (smooth polar loop — closes by construction),
  * grip-limited speed from curvature with forward/backward accel-brake passes
    (a proper racing-line speed profile, so braking + acceleration zones are real),
  * rpm proportional to speed per gear + a throttle lift at each up-shift.

Two laps: a committed fast lap and a slower lap (less lateral grip + a wheelspin
on one corner exit). Columns mimic a logger:
    time_s, lap, dist_m, speed_kph, engine_rpm, gear, throttle_pct, brake, pos_x, pos_y

    cd backend && python scripts/gen_sim_sample.py
"""
import csv
from pathlib import Path

import numpy as np
from scipy.integrate import cumulative_trapezoid

DS = 1.0          # metres between samples along the track
VMAX = 29.5       # m/s (~106 km/h)
A_ACC = 6.0       # m/s^2 forward
A_BRK = 13.5      # m/s^2 braking (~1.4g)
GEAR_TOP = np.array([0, 26, 46, 66, 86, 101, 116.0])
SHIFT_RPM = 12800.0


def centreline(n=2600):
    # Multiple harmonics -> several distinct corners (a real autocross shape),
    # amplitudes summing < 1 so the radius stays positive (no self-intersection).
    th = np.linspace(0.0, 2 * np.pi, n, endpoint=False)
    R = 165.0
    r = R * (1
             + 0.26 * np.sin(th + 0.3)
             + 0.20 * np.sin(2 * th + 1.0)
             + 0.15 * np.sin(3 * th + 2.1)
             + 0.11 * np.sin(4 * th + 0.6)
             + 0.07 * np.sin(5 * th + 1.7))
    return r * np.cos(th), r * np.sin(th)


def uniform_arclen(x, y, ds=DS):
    xc, yc = np.append(x, x[0]), np.append(y, y[0])       # close the loop
    s = np.concatenate([[0.0], np.cumsum(np.hypot(np.diff(xc), np.diff(yc)))])
    su = np.arange(0.0, s[-1], ds)                        # last point ~1 m before start
    return np.interp(su, s, xc), np.interp(su, s, yc), su


def curvature(x, y):
    dx, dy = np.gradient(x), np.gradient(y)
    ddx, ddy = np.gradient(dx), np.gradient(dy)
    return np.abs(dx * ddy - dy * ddx) / ((dx * dx + dy * dy) ** 1.5 + 1e-9)


def speed_profile(kappa, a_lat):
    v = np.clip(np.sqrt(a_lat / np.maximum(kappa, 1e-5)), 5.0, VMAX)
    n = len(v)
    for _ in range(3):                                    # accel limit (wrap-around)
        for i in range(n):
            v[i] = min(v[i], np.sqrt(v[i - 1] ** 2 + 2 * A_ACC * DS))
    for _ in range(3):                                    # brake limit (wrap-around)
        for i in range(n - 1, -1, -1):
            v[i] = min(v[i], np.sqrt(v[(i + 1) % n] ** 2 + 2 * A_BRK * DS))
    return v


def derive(v_kph):
    dv = np.gradient(v_kph / 3.6, DS)
    gear = np.clip(np.digitize(v_kph, [0, 25, 45, 65, 85, 100]), 1, 6)
    rpm = np.clip(SHIFT_RPM / GEAR_TOP[gear] * v_kph, 3000.0, 13500.0)
    throttle = np.where(dv >= -0.003, 100.0, 0.0)
    brake = (dv < -0.02).astype(float)
    for i in np.where(np.diff(gear) > 0)[0]:              # throttle lift at up-shifts
        lo, hi = max(0, i - 3), min(len(throttle), i + 4)
        throttle[lo:hi] = np.minimum(throttle[lo:hi], 20.0)
    return gear.astype(float), rpm, throttle, brake


def to_time_series(v_kph, gear, rpm, thr, brk, x, y, su):
    vms = np.clip(v_kph / 3.6, 1.0, None)
    t = cumulative_trapezoid(1.0 / vms, su, initial=0.0)
    tu = np.arange(0.0, t[-1], 0.05)
    R = lambda ch: np.interp(tu, t, ch)
    return {"t": tu, "dist": R(su), "speed": R(v_kph), "rpm": R(rpm),
            "gear": np.round(R(gear)), "thr": R(thr), "brk": np.round(R(brk)),
            "x": R(x), "y": R(y), "T": float(t[-1])}


def main():
    x, y, su = uniform_arclen(*centreline())
    kappa = curvature(x, y)

    v_fast = speed_profile(kappa, a_lat=12.5) * 3.6      # km/h
    v_slow = speed_profile(kappa, a_lat=10.6) * 3.6      # less commitment -> slower

    g_f, r_f, th_f, br_f = derive(v_fast)
    g_s, r_s, th_s, br_s = derive(v_slow)

    # wheelspin on the slow lap at the exit of the slowest corner (a loss corner),
    # so the physical-realism cross-check confirms it.
    apex = int(np.argmin(v_slow))
    spin = (np.arange(len(su)) > apex + 10) & (np.arange(len(su)) < apex + 40)
    r_s = r_s.copy(); r_s[spin] *= 1.16
    th_s = th_s.copy(); th_s[spin] = 100.0

    fast = to_time_series(v_fast, g_f, r_f, th_f, br_f, x, y, su)
    slow = to_time_series(v_slow, g_s, r_s, th_s, br_s, x, y, su)

    out = Path(__file__).resolve().parent.parent / "data" / "sample_sim" / "supra_autocross.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["time_s", "lap", "dist_m", "speed_kph", "engine_rpm",
                    "gear", "throttle_pct", "brake", "pos_x", "pos_y"])
        t0 = 0.0
        for lap, d in ((1, fast), (2, slow)):
            for i in range(len(d["t"])):
                w.writerow([round(t0 + d["t"][i], 3), lap, round(d["dist"][i], 2),
                            round(d["speed"][i], 2), int(round(d["rpm"][i])),
                            int(d["gear"][i]), round(d["thr"][i], 1), int(d["brk"][i]),
                            round(d["x"][i], 2), round(d["y"][i], 2)])
            t0 += d["T"] + 8.0

    gap0 = float(np.hypot(x[-1] - x[0], y[-1] - y[0]))
    span = max(x.max() - x.min(), y.max() - y.min())
    print(f"wrote {out}")
    print(f"track length {su[-1]:.0f} m, closure gap {gap0:.1f} m ({gap0/span*100:.2f}% of span)")
    print(f"fast {fast['T']:.2f}s, slow {slow['T']:.2f}s, gap {slow['T']-fast['T']:+.2f}s, "
          f"vmax {v_fast.max():.0f} kph")


if __name__ == "__main__":
    main()
