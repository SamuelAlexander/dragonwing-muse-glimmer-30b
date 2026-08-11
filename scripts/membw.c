// Multi-threaded memory read-bandwidth probe.
// Decode speed for a dense LLM is bounded by how fast the CPU can stream the
// weight matrix out of DRAM once per token, so peak read bandwidth is the
// ceiling we care about: tokens/s <= bandwidth / model_size_bytes.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <pthread.h>

#define GB (1024UL * 1024UL * 1024UL)

static size_t buf_bytes;
static char *buf;
static int nthreads;

static double now(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec * 1e-9;
}

// Read-only sum over a slice; volatile accumulator keeps it from being optimised out.
static void *read_worker(void *arg) {
    long id = (long)arg;
    size_t chunk = buf_bytes / nthreads;
    unsigned long long *p = (unsigned long long *)(buf + id * chunk);
    size_t n = chunk / sizeof(unsigned long long);
    unsigned long long acc = 0;
    for (size_t i = 0; i < n; i += 8) {
        acc += p[i] + p[i+1] + p[i+2] + p[i+3] + p[i+4] + p[i+5] + p[i+6] + p[i+7];
    }
    static volatile unsigned long long sink;
    sink = acc;
    return NULL;
}

int main(int argc, char **argv) {
    double gb = argc > 1 ? atof(argv[1]) : 4.0;
    int max_t = argc > 2 ? atoi(argv[2]) : 8;
    buf_bytes = (size_t)(gb * GB);
    buf = aligned_alloc(4096, buf_bytes);
    if (!buf) { fprintf(stderr, "alloc failed\n"); return 1; }
    memset(buf, 1, buf_bytes);  // fault every page in before timing

    printf("buffer: %.1f GiB\n", gb);
    printf("threads   read GB/s\n");
    for (nthreads = 1; nthreads <= max_t; nthreads *= 2) {
        double best = 0;
        for (int rep = 0; rep < 3; rep++) {
            pthread_t th[64];
            double t0 = now();
            for (long i = 0; i < nthreads; i++) pthread_create(&th[i], NULL, read_worker, (void *)i);
            for (long i = 0; i < nthreads; i++) pthread_join(th[i], NULL);
            double dt = now() - t0;
            double bw = buf_bytes / dt / 1e9;
            if (bw > best) best = bw;
        }
        printf("%7d   %8.1f\n", nthreads, best);
    }
    free(buf);
    return 0;
}
