"""Fast flood envelope along a river path (option B in the plan).

Not a hydrodynamic model. Two calibrated 1-D curves along river distance from the source:
  arrival(km) : minutes after the burst when the first wave arrives
  height(km)  : peak flood height above the DEM channel (m)
Each cell inherits the values of the channel cell it drains into (engine.terrain.hand_to).
A cell is in the flood footprint if HAND <= height. Bands (lo/hi) carry the uncertainty;
SAFE ground uses the conservative (hi) height plus a margin.
Calibration knots come from replay files (e.g. replay/oct11.json); see calibrate_from_replay().
"""
import numpy as np


class FloodEnvelope:
    def __init__(self, arrival_knots, height_knots, decay_km=30.0, floor_m=3.0,
                 time_band=0.25, height_band=0.30):
        self.ak = np.array(sorted(arrival_knots), float)   # [(km, minutes)]
        self.hk = np.array(sorted(height_knots), float)    # [(km, metres)]
        self.decay_km, self.floor_m = decay_km, floor_m
        self.time_band, self.height_band = time_band, height_band

    def arrival(self, km):
        km = np.asarray(km, float); k, t = self.ak[:, 0], self.ak[:, 1]
        slope = (t[-1] - t[-2]) / (k[-1] - k[-2])            # extrapolate with last wave speed
        return np.where(km <= k[-1], np.interp(km, k, t), t[-1] + (km - k[-1]) * slope)

    def arrival_band(self, km):
        a = self.arrival(km)
        return a * (1 - self.time_band), a, a * (1 + self.time_band)

    def height(self, km):
        km = np.asarray(km, float); k, h = self.hk[:, 0], self.hk[:, 1]
        beyond = self.floor_m + (h[-1] - self.floor_m) * np.exp(-(km - k[-1]) / self.decay_km)
        return np.where(km <= k[-1], np.interp(km, k, h), beyond)

    def height_band_at(self, km):
        h = self.height(km)
        return h * (1 - self.height_band), h, h * (1 + self.height_band)

    def wave_speed_kmh(self):
        k, t = self.ak[:, 0], self.ak[:, 1]
        return [(float(k[i]), float(k[i + 1]), float((k[i + 1] - k[i]) / ((t[i + 1] - t[i]) / 60)))
                for i in range(len(k) - 1)]


def hhmm_to_min(s):
    h, m = map(int, s.split(":")); return h * 60 + m


def calibrate_from_replay(rep, km_of):
    """Build arrival/height knots from a replay dict. km_of(lon, lat) -> river km from source."""
    t0 = hhmm_to_min(rep["burst_time"])
    ak, hk = [(0.0, 0.0)], []
    for o in rep["observations"]:
        if o.get("use") != "calibration":
            continue
        km = float(km_of(o["lon"], o["lat"]))
        if not np.isfinite(km):                                # outside the grid / not draining to the path
            continue
        if "first_arrival" in o:
            ak.append((km, hhmm_to_min(o["first_arrival"]) - t0))
        if "peak_height_m" in o:
            hk.append((km, float(np.mean(o["peak_height_m"]))))
        elif "gauge_peak_m" in o:
            hk.append((km, float(o["gauge_peak_m"]) - 2.4))   # stage rise above assumed ~2.4 m normal stage (assumption)
    if hk and hk[0][0] > 0:
        hk.insert(0, (0.0, hk[0][1]))                          # hold source height = first observed
    if not hk:
        raise ValueError(f"{rep['event']}: no height observation inside this grid; pass a FloodEnvelope "
                         "(e.g. models/damage/aug26_damage_envelope.json) instead")
    return FloodEnvelope(ak, hk)
