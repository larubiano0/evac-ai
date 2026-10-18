/* Dense MLP forward pass on the IBM Telum on-chip AI accelerator (NNPA), through IBM's zDNN library.
 *
 * Built as a shared library and driven from Python (ctypes; engine/surrogate.py, scripts/nnpa/bench_mlp.py):
 *   gcc -O2 -shared -fPIC -I<zdnn>/usr/include zdnn_mlp.c -L<zdnn>/usr/lib/s390x-linux-gnu -lzdnn -o zdnn_mlp.so
 *
 * Rows are stacked as a 3DS tensor [s, m, n] (s * m = rows per chunk); each layer is one zdnn_matmul_bcast_op
 * (x @ W + b, weights broadcast over the stack) followed by zdnn_relu, and the last layer by zdnn_sigmoid.
 * nnpa_create() converts the weights to the accelerator format and allocates the activations once (as a server
 * does at start-up); nnpa_run() is fp32 rows in -> accelerator format -> all layers -> fp32 out.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <zdnn.h>

#define MAXL 16
#define CHECK(x) do { zdnn_status st_ = (x); if (st_ != ZDNN_OK) { \
  fprintf(stderr, "zdnn error 0x%x at %s:%d\n", st_, __FILE__, __LINE__); return -1; } } while (0)

typedef struct {
  int nl;
  zdnn_tensor_desc pre[4 * MAXL + 4], tf[4 * MAXL + 4];
  zdnn_ztensor w[MAXL], b[MAXL], h[MAXL + 1], a[MAXL + 1];
} net_t;

static double now(void) {
  struct timespec t;
  clock_gettime(CLOCK_MONOTONIC, &t);
  return t.tv_sec + t.tv_nsec * 1e-9;
}

static int make(zdnn_ztensor *zt, zdnn_tensor_desc *pre, zdnn_tensor_desc *tf, zdnn_data_layouts lay,
                uint32_t a, uint32_t b, uint32_t c) {
  if (lay == ZDNN_1D) zdnn_init_pre_transformed_desc(lay, FP32, pre, a);
  else if (lay == ZDNN_2D) zdnn_init_pre_transformed_desc(lay, FP32, pre, a, b);
  else zdnn_init_pre_transformed_desc(lay, FP32, pre, a, b, c);
  CHECK(zdnn_generate_transformed_desc(pre, tf));
  CHECK(zdnn_init_ztensor_with_malloc(pre, tf, zt));
  return 0;
}

uint32_t nnpa_max_dim(void) { return zdnn_get_nnpa_max_dim_idx_size(); }
int nnpa_available(void) { zdnn_init(); return zdnn_is_nnpa_installed(); }

/* dims[0] = inputs, dims[1..nl] = layer widths; W[l] is dims[l] x dims[l+1] row-major, B[l] has dims[l+1].
 * Each nnpa_run() call scores exactly s*m rows. */
void *nnpa_create(uint32_t s, uint32_t m, int nl, const int *dims, const float **W, const float **B) {
  if (nl < 1 || nl > MAXL) return NULL;
  zdnn_init();
  net_t *n = calloc(1, sizeof(net_t));
  int k = 0;
  n->nl = nl;
  for (int l = 0; l < nl; l++) {
    if (make(&n->w[l], &n->pre[k], &n->tf[k], ZDNN_2D, dims[l], dims[l + 1], 0)) return NULL;
    k++;
    if (make(&n->b[l], &n->pre[k], &n->tf[k], ZDNN_1D, dims[l + 1], 0, 0)) return NULL;
    k++;
    if (zdnn_transform_ztensor(&n->w[l], W[l]) != ZDNN_OK) return NULL;
    if (zdnn_transform_ztensor(&n->b[l], B[l]) != ZDNN_OK) return NULL;
  }
  for (int l = 0; l <= nl; l++) {
    if (make(&n->a[l], &n->pre[k], &n->tf[k], ZDNN_3DS, s, m, dims[l])) return NULL;            /* activations */
    k++;
    if (l > 0 && make(&n->h[l], &n->pre[k], &n->tf[k], ZDNN_3DS, s, m, dims[l])) return NULL;   /* pre-act */
    k++;
  }
  return n;
}

/* t (may be NULL): t[0] += wall seconds for the whole call, t[1] += seconds for the layers only. */
int nnpa_run(void *net, const float *x, float *out, double *t) {
  net_t *n = net;
  double t0 = now();
  n->a[0].is_transformed = false;
  CHECK(zdnn_transform_ztensor(&n->a[0], x));
  double t1 = now();
  for (int l = 0; l < n->nl; l++) {
    n->h[l + 1].is_transformed = false;
    n->a[l + 1].is_transformed = false;
    CHECK(zdnn_matmul_bcast_op(&n->a[l], &n->w[l], &n->b[l], MATMUL_BCAST_OP_ADDITION, &n->h[l + 1]));
    if (l + 1 < n->nl) CHECK(zdnn_relu(&n->h[l + 1], NULL, &n->a[l + 1]));
    else CHECK(zdnn_sigmoid(&n->h[l + 1], &n->a[l + 1]));
  }
  double t2 = now();
  CHECK(zdnn_transform_origtensor(&n->a[n->nl], out));
  if (t) { t[0] += now() - t0; t[1] += t2 - t1; }
  return 0;
}

void nnpa_free(void *net) {
  net_t *n = net;
  if (!n) return;
  for (int l = 0; l < n->nl; l++) { zdnn_free_ztensor_buffer(&n->w[l]); zdnn_free_ztensor_buffer(&n->b[l]); }
  for (int l = 0; l <= n->nl; l++) {
    zdnn_free_ztensor_buffer(&n->a[l]);
    if (l > 0) zdnn_free_ztensor_buffer(&n->h[l]);
  }
  free(n);
}

/* One-shot benchmark helper: times[0] = best end-to-end, times[1] = best layers-only, over reps after a warm-up. */
int mlp_nnpa(const float *x, uint32_t s, uint32_t m, int nl, const int *dims, const float **W, const float **B,
             float *out, int reps, double *times) {
  void *n = nnpa_create(s, m, nl, dims, W, B);
  if (!n) return -1;
  times[0] = times[1] = 1e30;
  for (int r = 0; r <= reps; r++) {
    double t[2] = {0, 0};
    if (nnpa_run(n, x, out, t)) { nnpa_free(n); return -1; }
    if (r > 0) {
      if (t[0] < times[0]) times[0] = t[0];
      if (t[1] < times[1]) times[1] = t[1];
    }
  }
  nnpa_free(n);
  return 0;
}
