/* Dense MLP forward pass on the IBM Telum on-chip AI accelerator (NNPA), through IBM's zDNN library.
 *
 * Built as a shared library and driven from scripts/nnpa/bench_mlp.py (ctypes):
 *   gcc -O2 -shared -fPIC -I<zdnn>/usr/include zdnn_mlp.c -L<zdnn>/usr/lib/s390x-linux-gnu -lzdnn -o zdnn_mlp.so
 *
 * Rows are stacked as a 3DS tensor [s, m, n] (s * m = rows); each layer is one zdnn_matmul_bcast_op
 * (x @ W + b, weights broadcast over the stack) followed by zdnn_relu, and the last layer by zdnn_sigmoid.
 * Weights are transformed to the accelerator format once (as a server would at start-up); the timed part is
 * fp32 input -> accelerator format -> all layers -> fp32 output.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <zdnn.h>

#define CHECK(x) do { zdnn_status st_ = (x); if (st_ != ZDNN_OK) { \
  fprintf(stderr, "zdnn error 0x%x at %s:%d\n", st_, __FILE__, __LINE__); return -1; } } while (0)

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
int nnpa_available(void) { return zdnn_is_nnpa_installed(); }

/* dims[0] = inputs, dims[1..nl] = layer widths; W[l] is dims[l] x dims[l+1] row-major, B[l] has dims[l+1].
 * x is s*m x dims[0]; out gets s*m x dims[nl]. times[0] = best end-to-end, times[1] = best layers-only. */
int mlp_nnpa(const float *x, uint32_t s, uint32_t m, int nl, const int *dims, const float **W, const float **B,
             float *out, int reps, double *times) {
  zdnn_init();
  zdnn_tensor_desc pre[64], tf[64];
  zdnn_ztensor w[16], b[16], h[17], a[17];
  int k = 0;
  for (int l = 0; l < nl; l++) {
    if (make(&w[l], &pre[k], &tf[k], ZDNN_2D, dims[l], dims[l + 1], 0)) return -1; k++;
    if (make(&b[l], &pre[k], &tf[k], ZDNN_1D, dims[l + 1], 0, 0)) return -1; k++;
    CHECK(zdnn_transform_ztensor(&w[l], W[l]));
    CHECK(zdnn_transform_ztensor(&b[l], B[l]));
  }
  for (int l = 0; l <= nl; l++) {
    if (make(&a[l], &pre[k], &tf[k], ZDNN_3DS, s, m, dims[l])) return -1; k++;   /* activations */
    if (l > 0) { if (make(&h[l], &pre[k], &tf[k], ZDNN_3DS, s, m, dims[l])) return -1; k++; }  /* pre-act */
  }
  times[0] = times[1] = 1e30;
  for (int r = 0; r <= reps; r++) {       /* r == 0 is the warm-up */
    double t0 = now();
    a[0].is_transformed = false;
    CHECK(zdnn_transform_ztensor(&a[0], x));
    double t1 = now();
    for (int l = 0; l < nl; l++) {
      h[l + 1].is_transformed = false;
      a[l + 1].is_transformed = false;
      CHECK(zdnn_matmul_bcast_op(&a[l], &w[l], &b[l], MATMUL_BCAST_OP_ADDITION, &h[l + 1]));
      if (l + 1 < nl) CHECK(zdnn_relu(&h[l + 1], NULL, &a[l + 1]));
      else CHECK(zdnn_sigmoid(&h[l + 1], &a[l + 1]));
    }
    double t2 = now();
    CHECK(zdnn_transform_origtensor(&a[nl], out));
    double t3 = now();
    if (r > 0) {
      if (t3 - t0 < times[0]) times[0] = t3 - t0;
      if (t2 - t1 < times[1]) times[1] = t2 - t1;
    }
  }
  for (int l = 0; l < nl; l++) { zdnn_free_ztensor_buffer(&w[l]); zdnn_free_ztensor_buffer(&b[l]); }
  for (int l = 0; l <= nl; l++) { zdnn_free_ztensor_buffer(&a[l]); if (l > 0) zdnn_free_ztensor_buffer(&h[l]); }
  return 0;
}
