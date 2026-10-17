/* Time-dependent fastest escape on a 30 m grid (used by engine/escape.py through ctypes).
 *
 * From one start cell at time t0 (minutes after the flood starts), expand 8-neighbour moves with
 * Tobler hiking-function walking times on the DEM. A cell v can be entered at time T(v) unless
 *   blocked[v]                         (flood river strip; bridges are not blocked), or
 *   p[v] > tau  and  T(v) >= A[v]      (risky cell reached when the flood is already there).
 * The search stops at the first settled cell with p <= goal_p (the closest place, by walking time, that is
 * safe to stay on). Passability (tau) and the goal (goal_p) are separate: the caller passes goal_p = UNSAFE_P
 * to always end on safe ground, or goal_p = tau for the best-effort fallback.
 * goal_p < 0: never stop (fills T for every reachable cell; the caller picks the destination).
 * Pace: Tobler walking, or "running" = run_factor x walking speed for the first run_min minutes of the trip
 * (elapsed = T(u) - t0), then walking again; an edge that straddles run_min is split exactly.
 * Arrival stays monotone in departure time (FIFO), so label-setting Dijkstra is exact.
 * Returns the goal index (or -1), fills T (minutes, INFINITY if not reached) and prev (-1 = none).
 */
#include <math.h>
#include <stdlib.h>

typedef struct { double t; int i; } Item;

static void push(Item *h, int *n, double t, int i) {
    int k = (*n)++;
    while (k > 0) {
        int p = (k - 1) / 2;
        if (h[p].t <= t) break;
        h[k] = h[p]; k = p;
    }
    h[k].t = t; h[k].i = i;
}

static Item pop(Item *h, int *n) {
    Item top = h[0], last = h[--(*n)];
    int k = 0;
    for (;;) {
        int c = 2 * k + 1;
        if (c >= *n) break;
        if (c + 1 < *n && h[c + 1].t < h[c].t) c++;
        if (h[c].t >= last.t) break;
        h[k] = h[c]; k = c;
    }
    h[k] = last;
    return top;
}

/* Tobler (1993): v = 6 exp(-3.5 |S + 0.05|) km/h, S = dz/dx (uphill positive); off-path x 0.6. */
static double walk_min(double dist_m, double dz, int on_trail) {
    double s = dz / dist_m;
    double v_kmh = 6.0 * exp(-3.5 * fabs(s + 0.05)) * (on_trail ? 1.0 : 0.6);
    return dist_m / (v_kmh * 1000.0 / 60.0);
}

/* minutes to cross an edge of walking time c, leaving after e minutes of travel */
static double edge_min(double c, double e, double run_factor, double run_min) {
    if (run_factor <= 1.0 || e >= run_min) return c;
    double cr = c / run_factor;
    if (e + cr <= run_min) return cr;
    double f = (run_min - e) / cr;                 /* fraction of the edge covered running */
    return (run_min - e) + (1.0 - f) * c;
}

int escape_search(int nr, int nc, const float *dem, const unsigned char *trail, const unsigned char *blocked,
                  const float *p, const float *A, int start, double t0, double tau, double cell,
                  double *T, int *prev, double goal_p, double run_factor, double run_min) {
    int N = nr * nc, n = 0, goal = -1;
    static const int dr[8] = {-1, -1, -1, 0, 0, 1, 1, 1}, dc[8] = {-1, 0, 1, -1, 1, -1, 0, 1};
    unsigned char *done = calloc(N, 1);
    Item *h = malloc(sizeof(Item) * (size_t)(8 * N + 8));
    if (!done || !h) { free(done); free(h); return -2; }
    for (int i = 0; i < N; i++) { T[i] = INFINITY; prev[i] = -1; }
    T[start] = t0; push(h, &n, t0, start);
    while (n > 0) {
        Item it = pop(h, &n);
        int u = it.i;
        if (done[u] || it.t > T[u]) continue;
        done[u] = 1;
        if (u != start && p[u] <= goal_p) { goal = u; break; }
        int r = u / nc, c = u % nc;
        for (int k = 0; k < 8; k++) {
            int rr = r + dr[k], cc = c + dc[k];
            if (rr < 0 || rr >= nr || cc < 0 || cc >= nc) continue;
            int v = rr * nc + cc;
            if (done[v] || blocked[v] || !isfinite(dem[v])) continue;
            double d = (dr[k] && dc[k]) ? cell * 1.41421356237 : cell;
            double c = walk_min(d, (double)dem[v] - (double)dem[u], trail[u] && trail[v]);
            double tv = T[u] + edge_min(c, T[u] - t0, run_factor, run_min);
            if (p[v] > tau && tv >= A[v]) continue;          /* flood is already there */
            if (tv < T[v]) { T[v] = tv; prev[v] = u; push(h, &n, tv, v); }
        }
    }
    free(done); free(h);
    return goal;
}
