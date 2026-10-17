"""Terrain model on top of GRASS r.watershed outputs.

Loads the DEM and D8 drainage directions (GRASS encoding: value*45 = degrees CCW from East,
i.e. 1=NE 2=N 3=NW 4=W 5=SW 6=S 7=SE 8=E; <=0 = flows out of region / undefined).

Key operation: hand_to(channel_mask) -> Height Above Nearest Drainage *measured against a given
channel set* (e.g. the river reach a flood travels down), plus the index of the channel cell each
cell drains into. Standard HAND definition (Nobre et al. 2011) via pointer jumping on the D8 graph.
"""
import numpy as np
import rasterio

# GRASS r.watershed direction code -> (drow, dcol); rows increase southwards.
_D = {1: (-1, 1), 2: (-1, 0), 3: (-1, -1), 4: (0, -1), 5: (1, -1), 6: (1, 0), 7: (1, 1), 8: (0, 1)}


class Terrain:
    def __init__(self, proc_dir="data/proc"):
        with rasterio.open(f"{proc_dir}/dem_g.tif") as r:
            self.dem = r.read(1).astype(np.float64)
            self.transform, self.crs = r.transform, r.crs
        with rasterio.open(f"{proc_dir}/sdir.tif") as r:
            d = r.read(1).astype(np.int16)
        with rasterio.open(f"{proc_dir}/streams.tif") as r:
            s = r.read(1)
        with rasterio.open(f"{proc_dir}/acc.tif") as r:
            self.acc = np.abs(r.read(1).astype(np.float64))
        self.shape = self.dem.shape
        self.streams = (s > 0) & (s != np.iinfo(np.int32).min)
        self.nxt = self._next_index(d)          # flat index of downstream cell (self if none)

    def _next_index(self, d):
        nr, nc = self.shape
        rows, cols = np.indices(self.shape)
        nxt = np.arange(nr * nc, dtype=np.int64).reshape(self.shape)
        for code, (dr, dc) in _D.items():
            m = d == code
            r2, c2 = rows[m] + dr, cols[m] + dc
            ok = (r2 >= 0) & (r2 < nr) & (c2 >= 0) & (c2 < nc)
            idx = np.flatnonzero(m)[ok]
            nxt.flat[idx] = r2[ok] * nc + c2[ok]
        return nxt.ravel()

    # ---------- coordinates ----------
    def rc(self, x, y):
        c, r = ~self.transform * (x, y)
        return int(r), int(c)

    def xy(self, r, c):
        return self.transform * (c + 0.5, r + 0.5)

    # ---------- flow paths ----------
    def downstream_path(self, r, c, max_steps=200000):
        """Flat indices from (r,c) following D8 until it leaves the grid or stops."""
        i = r * self.shape[1] + c
        path = [i]
        for _ in range(max_steps):
            j = self.nxt[i]
            if j == i:
                break
            path.append(j); i = j
        return np.array(path, dtype=np.int64)

    def snap_to_channel(self, r, c, radius=10):
        """Move a point to the highest-accumulation stream cell within `radius` cells."""
        r0, r1 = max(r - radius, 0), min(r + radius + 1, self.shape[0])
        c0, c1 = max(c - radius, 0), min(c + radius + 1, self.shape[1])
        win = np.where(self.streams[r0:r1, c0:c1], self.acc[r0:r1, c0:c1], -1)
        k = np.unravel_index(np.argmax(win), win.shape)
        return r0 + k[0], c0 + k[1]

    # ---------- HAND ----------
    def hand_to(self, channel_flat_idx):
        """HAND relative to the given channel cells. Returns (hand[m], drain_idx) as 2D arrays;
        cells that never drain into the channel get NaN / -1."""
        n = self.nxt.size
        is_ch = np.zeros(n, bool); is_ch[channel_flat_idx] = True
        p = self.nxt.copy()
        p[is_ch] = np.flatnonzero(is_ch)                     # channel cells point to themselves
        for _ in range(40):                                   # pointer jumping: 2^40 >> any path length
            q = p[p]
            q[is_ch] = p[is_ch]
            if np.array_equal(q, p):
                break
            p = q
        reached = is_ch[p]
        dem = self.dem.ravel()
        hand = np.where(reached, dem - dem[p], np.nan)
        drain = np.where(reached, p, -1)
        return hand.reshape(self.shape), drain.reshape(self.shape)

    def check_directions(self):
        """Fraction of cells whose D8 successor is not higher (should be ~1)."""
        dem = self.dem.ravel(); moved = self.nxt != np.arange(self.nxt.size)
        return float((dem[self.nxt[moved]] <= dem[moved] + 1e-6).mean()), float(moved.mean())
