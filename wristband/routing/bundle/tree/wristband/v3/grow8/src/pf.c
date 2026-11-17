/* [grow G-2] PathFinder negotiated-congestion grid router core for the SolarBand V3-F board.
 * [grow8] mask bits: 0..NL-1 track legal per signal layer (NL <= 6), 64 via legal, 128 plane via.
 * Grid: NL signal layers x NY x NX cells (0.025 mm). Static rules (fixed copper of other nets, holes, keep-outs, edge, plates, R-2)
 * come in as one bit mask per net window (bit l = track allowed on layer l, bit 5 = via allowed, bit 6 = plane via allowed).
 * Dynamic rules (routed copper of other nets) are occupancy fields: every routed element of net m is stamped into field k with
 * radius halo(m) + B_k + margin, so a track of a net of class k at cell c clears all other routed copper iff fieldT[k][c] == 0
 * (via: fieldV[kv][c] == 0, union over layers). Shared cells cost (b + h) * (1 + pres * occ) (PathFinder); history grows on
 * overused cells every iteration; only nets with overuse or failures are rerouted after the first iteration.
 * Build: cc -O3 -shared -fPIC -o libpf.so pf.c -lm
 */
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#ifndef LEGAL_SUPPORT
#define LEGAL_SUPPORT 0
#endif

typedef struct {
    int32_t NL, NY, NX, NNET;
    const int16_t *lab;                 /* [NL*NY*NX] fixed copper owner (net id, -1 netless, 0 none) */
    const uint8_t *mask;                /* concatenated per-net window masks */
    const int64_t *m_off;               /* [NNET+1] */
    const int32_t *win;                 /* [NNET+1][4] j0 j1 i0 i1 */
    const int32_t *kT, *kV, *plane;     /* [NNET+1] */
    const float *At, *Av, *vhole;       /* [NNET+1] halo of a track / via of the net (mm), via hole radius (mm) */
    int32_t nKT, nKV;
    const float *BT, *BV;               /* checker radius per class (mm) */
    float grid, margin;
    float lc[8];                        /* layer cost */
    float via_cost;                     /* grid units */
    int32_t NC;
    const int32_t *c_net, *c_ga, *c_gb; /* [NC] */
    int32_t NG;
    const int64_t *g_off;               /* [NG+1] */
    const int32_t *g_cells;             /* node indices */
    const int32_t *g_onplane;           /* [NG] */
    const int32_t *g_net;               /* [NG] */
    int32_t NORD;
    const int32_t *order;               /* nets in routing order */
    const int64_t *nc_off;              /* [NNET+2] connections per net (net id indexed) */
    const int32_t *nc_list;
    int32_t max_iter, reroute_all;      /* reroute_all: number of first iterations that rip every net */
    float pres0, pres_mult, hist_inc, hw;
    int64_t max_exp;
    float conn_margin;                  /* mm, first search window around the connection */
    float tlim;                         /* s */
    /* outputs */
    int32_t *out_status;                /* [NC] 0 unrouted, 1 routed, 2 skipped (already joined), 3 dropped in legalisation */
    float *it_stats;                    /* [max_iter][6]: overused nodes, unrouted conns, seconds, nets rerouted, expansions(M), pres */
    int32_t *n_iter;
    int32_t *final_over;
    /* [grow8 Q-2] neck-down: per-net window mask (same layout as mask), 1 = cell within the neck radius of an own pad: the track
       there is 0.09 wide (class kNeck, halo AtNeck). NULL = off. A step a->b is narrow iff a or b is in the zone. */
    const uint8_t *nmask;
    int32_t kNeck;
    float AtNeck;
} PF;

typedef struct { int32_t *n; int32_t len, cap; int32_t pv; } Path;   /* pv: last node gets a plane via */

static PF *P;
static int64_t N, P2;
static uint8_t **FT, **FV;
static float *hist, *histV, *gc;
static int32_t *prv, *seen, *tmark, *stampT, *stampV;
static int32_t tok_search = 0, tok_t = 0, tok_stamp = 0;
static Path *PA, *PB;                   /* per connection: main path, second path (plane nets) */
static int32_t *uf;                     /* union-find over groups */
static int32_t *gplane;                 /* cluster on plane (root-indexed) */
static int64_t nexp_tot;
static int32_t *supp, tok_supp = 0; static uint8_t *acc; static int n_dangling = 0;   /* [grow8] legalisation support check */

/* ------------------------------------------------------------------ heap */
typedef struct { float f; int32_t v; } HE;
static HE *heap; static int64_t hn, hcap;
static void hpush(float f, int32_t v) {
    if (hn >= hcap) { hcap = hcap ? hcap * 2 : 1 << 20; heap = realloc(heap, hcap * sizeof(HE)); }
    int64_t i = hn++;
    while (i > 0) { int64_t p = (i - 1) >> 1; if (heap[p].f <= f) break; heap[i] = heap[p]; i = p; }
    heap[i].f = f; heap[i].v = v;
}
static HE hpop(void) {
    HE top = heap[0], x = heap[--hn]; int64_t i = 0;
    for (;;) { int64_t c = 2 * i + 1; if (c >= hn) break; if (c + 1 < hn && heap[c + 1].f < heap[c].f) c++; if (heap[c].f >= x.f) break; heap[i] = heap[c]; i = c; }
    if (hn > 0) heap[i] = x;
    return top;
}

static void padd(Path *p, int32_t v) {
    if (p->len >= p->cap) { p->cap = p->cap ? p->cap * 2 : 256; p->n = realloc(p->n, p->cap * sizeof(int32_t)); }
    p->n[p->len++] = v;
}

static int uf_find(int a) { while (uf[a] != a) { uf[a] = uf[uf[a]]; a = uf[a]; } return a; }

static inline uint8_t mbits(int n, int64_t c2) {          /* mask byte of net n at 2D cell c2, 0 outside its window */
    int j = (int)(c2 / P->NX), i = (int)(c2 % P->NX);
    const int32_t *w = P->win + 4 * n;
    if (j < w[0] || j >= w[1] || i < w[2] || i >= w[3]) return 0;
    return P->mask[P->m_off[n] + (int64_t)(j - w[0]) * (w[3] - w[2]) + (i - w[2])];
}

static inline int nbits(int n, int64_t c2) {               /* [grow8 Q-2] neck zone of net n at 2D cell c2 */
    if (!P->nmask) return 0;
    int j = (int)(c2 / P->NX), i = (int)(c2 % P->NX);
    const int32_t *w = P->win + 4 * n;
    if (j < w[0] || j >= w[1] || i < w[2] || i >= w[3]) return 0;
    return P->nmask[P->m_off[n] + (int64_t)(j - w[0]) * (w[3] - w[2]) + (i - w[2])];
}
static inline uint8_t *ftn(int n, int64_t c2) { return nbits(n, c2) ? FT[P->kNeck] : FT[P->kT[n]]; }

/* ------------------------------------------------------------------ stamping */
static void stamp_capsule(uint8_t *F, int is3d, int l, int j0, int i0, int j1, int i1, float r, int sign, int32_t *stamp, int32_t tok) {
    int R = (int)ceilf(r);
    int ja = (j0 < j1 ? j0 : j1) - R, jb = (j0 > j1 ? j0 : j1) + R, ia = (i0 < i1 ? i0 : i1) - R, ib = (i0 > i1 ? i0 : i1) + R;
    if (ja < 0) ja = 0; if (ia < 0) ia = 0; if (jb >= P->NY) jb = P->NY - 1; if (ib >= P->NX) ib = P->NX - 1;
    float dj = (float)(j1 - j0), di = (float)(i1 - i0), L2 = dj * dj + di * di, r2 = r * r;
    int64_t base = is3d ? (int64_t)l * P2 : 0;
    for (int j = ja; j <= jb; j++) {
        for (int i = ia; i <= ib; i++) {
            float t = 0.f;
            if (L2 > 0) { t = ((j - j0) * dj + (i - i0) * di) / L2; if (t < 0) t = 0; if (t > 1) t = 1; }
            float ej = j - j0 - t * dj, ei = i - i0 - t * di;
            if (ej * ej + ei * ei > r2) continue;
            int64_t c = base + (int64_t)j * P->NX + i;
            if (stamp[c] == tok) continue;
            stamp[c] = tok;
            int v = F[c] + sign; F[c] = (uint8_t)(v < 0 ? 0 : (v > 255 ? 255 : v));
        }
    }
}

/* walk a path as elements: straight runs (same layer, same step) and vias */
typedef void (*elem_fn)(int kind, int l, int j0, int i0, int j1, int i1, void *ctx);
/* kind 0 track, 1 via, 2 narrow (neck) track */
static void path_elems(const Path *p, int n, elem_fn fn, void *ctx) {
    if (p->len == 0) return;
    int64_t s = 0;
    while (s < p->len) {
        int32_t a = p->n[s]; int la = (int)(a / P2); int64_t ca = a % P2;
        if (s + 1 < p->len) {
            int32_t b = p->n[s + 1]; int lb = (int)(b / P2); int64_t cb = b % P2;
            if (lb != la) {                                      /* via */
                fn(1, la, (int)(ca / P->NX), (int)(ca % P->NX), 0, 0, ctx);
                s++; continue;
            }
            int64_t step = cb - ca, e = s + 1;
            int narrow = nbits(n, ca) | nbits(n, cb);
            if (narrow) { while (e + 1 < p->len && p->n[e + 1] / P2 == la && (p->n[e + 1] % P2) - (p->n[e] % P2) == step && nbits(n, p->n[e] % P2)) e++; }
            else { while (e + 1 < p->len && p->n[e + 1] / P2 == la && (p->n[e + 1] % P2) - (p->n[e] % P2) == step && !nbits(n, p->n[e + 1] % P2)) e++; }
            int64_t ce = p->n[e] % P2;
            fn(narrow ? 2 : 0, la, (int)(ca / P->NX), (int)(ca % P->NX), (int)(ce / P->NX), (int)(ce % P->NX), ctx);
            s = e;
            if (s == p->len - 1) break;
            continue;
        }
        fn(0, la, (int)(ca / P->NX), (int)(ca % P->NX), (int)(ca / P->NX), (int)(ca % P->NX), ctx);
        break;
    }
    if (p->pv) { int32_t a = p->n[p->len - 1]; int64_t ca = a % P2; fn(1, (int)(a / P2), (int)(ca / P->NX), (int)(ca % P->NX), 0, 0, ctx); }
}

typedef struct { int n, k, sign, field3d; int32_t tok; } SC;
static void stamp_elem(int kind, int l, int j0, int i0, int j1, int i1, void *vctx) {
    SC *c = (SC *)vctx; int n = c->n;
    float B = c->field3d ? P->BT[c->k] : P->BV[c->k];
    float A = kind == 1 ? P->Av[n] : (kind == 2 ? P->AtNeck : P->At[n]);
    float r = (A + B + P->margin) / P->grid;
    if (c->field3d) {
        if (kind == 1) { for (int ll = 0; ll < P->NL; ll++) stamp_capsule(FT[c->k], 1, ll, j0, i0, j0, i0, r, c->sign, stampT, c->tok); }
        else stamp_capsule(FT[c->k], 1, l, j0, i0, j1, i1, r, c->sign, stampT, c->tok);
    } else {
        if (kind == 1) stamp_capsule(FV[c->k], 0, 0, j0, i0, j0, i0, r, c->sign, stampV, c->tok);
        else stamp_capsule(FV[c->k], 0, 0, j0, i0, j1, i1, r, c->sign, stampV, c->tok);
    }
}

static void stamp_net(int n, int sign) {
    SC c; c.n = n; c.sign = sign;
    for (int k = 0; k < P->nKT; k++) {
        c.k = k; c.field3d = 1; c.tok = ++tok_stamp;
        for (int64_t q = P->nc_off[n]; q < P->nc_off[n + 1]; q++) { int ci = P->nc_list[q]; path_elems(&PA[ci], n, stamp_elem, &c); path_elems(&PB[ci], n, stamp_elem, &c); }
    }
    for (int k = 0; k < P->nKV; k++) {
        c.k = k; c.field3d = 0; c.tok = ++tok_stamp;
        for (int64_t q = P->nc_off[n]; q < P->nc_off[n + 1]; q++) { int ci = P->nc_list[q]; path_elems(&PA[ci], n, stamp_elem, &c); path_elems(&PB[ci], n, stamp_elem, &c); }
    }
}

/* ------------------------------------------------------------------ overuse of a net's paths (net is stamped) */
typedef struct { int n; int64_t over; int upd; } OC;
static void over_node(OC *o, int32_t v, int via) {
    int n = o->n; int64_t c2 = v % P2;
    if (via) {
        if (FV[P->kV[n]][c2] > 1) { o->over++; if (o->upd) histV[c2] += P->hist_inc; }
    } else {
        if (P->lab[v] == n) return;
        if (ftn(n, c2)[v] > 1) { o->over++; if (o->upd) hist[v] += P->hist_inc; }
    }
}
static int64_t net_over(int n, int upd) {
    OC o; o.n = n; o.over = 0; o.upd = upd;
    for (int64_t q = P->nc_off[n]; q < P->nc_off[n + 1]; q++) {
        int ci = P->nc_list[q];
        for (int pp = 0; pp < 2; pp++) {
            Path *p = pp ? &PB[ci] : &PA[ci];
            for (int32_t k = 0; k < p->len; k++) {
                int via = (k + 1 < p->len && p->n[k + 1] / P2 != p->n[k] / P2);
                over_node(&o, p->n[k], via);
            }
            if (p->pv && p->len) over_node(&o, p->n[p->len - 1], 1);
        }
    }
    return o.over;
}

/* ------------------------------------------------------------------ own new vias of the net being routed (hole to hole) */
static int32_t *ownv; static int nownv, capownv;
static int ownvia_ok(int n, int64_t c2) {
    float dmin = (2 * P->vhole[n] + 0.20f + P->margin) / P->grid; float d2 = dmin * dmin;
    int j = (int)(c2 / P->NX), i = (int)(c2 % P->NX);
    for (int k = 0; k < nownv; k++) { int jj = ownv[k] / P->NX, ii = ownv[k] % P->NX; float a = j - jj, b = i - ii; if (a * a + b * b < d2 && ownv[k] != c2) return 0; }
    return 1;
}
static void ownv_add(int32_t c2) { if (nownv >= capownv) { capownv = capownv ? capownv * 2 : 64; ownv = realloc(ownv, capownv * sizeof(int32_t)); } ownv[nownv++] = c2; }
static void ownv_collect(const Path *p) {
    for (int32_t k = 0; k + 1 < p->len; k++) if (p->n[k + 1] / P2 != p->n[k] / P2) ownv_add((int32_t)(p->n[k] % P2));
    if (p->pv && p->len) ownv_add((int32_t)(p->n[p->len - 1] % P2));
}

/* ------------------------------------------------------------------ A* search for one connection */
static const int DJ[8] = {-1, 1, 0, 0, -1, -1, 1, 1}, DI[8] = {0, 0, -1, 1, -1, 1, -1, 1};
static const float DC[8] = {1, 1, 1, 1, 1.41421356f, 1.41421356f, 1.41421356f, 1.41421356f};

/* sources: nodes with seen==tok_search set before; targets: tmark==tok_t. hard: occupied cells blocked */
static int astar(int n, float pres, int hard, int planegoal, int bj0, int bj1, int bi0, int bi1, int tj0, int tj1, int ti0, int ti1, Path *out) {
    const int NX = P->NX; int kt = P->kT[n], kv = P->kV[n];
    uint8_t *ft = FT[kt], *fv = FV[kv];
    int64_t nexp = 0; int32_t goal = -1; int pv = 0;
    float hwv = planegoal ? 0.f : P->hw;
    while (hn > 0) {
        HE e = hpop(); int32_t u = e.v;
        float gu = gc[u];
        int64_t c2 = u % P2; int l = (int)(u / P2); int j = (int)(c2 / NX), i = (int)(c2 % NX);
        float hu = 0.f;
        if (hwv > 0) { int dy = j < tj0 ? tj0 - j : (j > tj1 ? j - tj1 : 0), dx = i < ti0 ? ti0 - i : (i > ti1 ? i - ti1 : 0);
                       int mx = dx > dy ? dx : dy, mn = dx > dy ? dy : dx; hu = hwv * (mx + 0.41421356f * mn); }
        if (e.f > gu + hu + 1e-3f) continue;               /* stale */
        if (++nexp > P->max_exp) break;
        if (tmark[u] == tok_t) { goal = u; break; }
        uint8_t mb = mbits(n, c2);
        if (planegoal && (mb & 128) && ownvia_ok(n, c2) && (hard ? fv[c2] == 0 : 1)) { goal = u; pv = 1; break; }
        for (int d = 0; d < 8; d++) {
            int jj = j + DJ[d], ii = i + DI[d];
            if (jj < bj0 || jj >= bj1 || ii < bi0 || ii >= bi1) continue;
            int64_t c2v = (int64_t)jj * NX + ii; int32_t v = (int32_t)(l * P2 + c2v);
            uint8_t mv = mbits(n, c2v);
            if (!(mv & (1 << l)) && tmark[v] != tok_t) continue;
            int own = P->lab[v] == n; int occ = own ? 0 : (nbits(n, c2v) ? FT[P->kNeck] : ft)[v];
            if (hard && occ) continue;
            float cst = DC[d] * (P->lc[l] + hist[v]) * (1.f + pres * occ);
            float ng = gu + cst;
            if (seen[v] != tok_search || ng < gc[v]) {
                seen[v] = tok_search; gc[v] = ng; prv[v] = u;
                int dy = jj < tj0 ? tj0 - jj : (jj > tj1 ? jj - tj1 : 0), dx = ii < ti0 ? ti0 - ii : (ii > ti1 ? ii - ti1 : 0);
                int mx = dx > dy ? dx : dy, mn = dx > dy ? dy : dx;
                hpush(ng + hwv * (mx + 0.41421356f * mn), v);
            }
        }
        if (mb & 64) {
            int occv = fv[c2];
            if (!(hard && occv) && ownvia_ok(n, c2)) {
                float cst = P->via_cost * (1.f + histV[c2]) * (1.f + pres * occv);
                for (int l2 = 0; l2 < P->NL; l2++) {
                    if (l2 == l) continue;
                    int32_t v = (int32_t)(l2 * P2 + c2);
                    if (!(mb & (1 << l2)) && tmark[v] != tok_t) continue;
                    int own = P->lab[v] == n; int occ = own ? 0 : (nbits(n, c2) ? FT[P->kNeck] : ft)[v];
                    if (hard && occ) continue;
                    float ng = gu + cst;
                    if (seen[v] != tok_search || ng < gc[v]) { seen[v] = tok_search; gc[v] = ng; prv[v] = u; hpush(ng + hu, v); }
                }
            }
        }
    }
    nexp_tot += nexp;
    hn = 0;
    out->len = 0; out->pv = 0;
    if (goal < 0) return 0;
    /* backtrack */
    int32_t v = goal; int64_t cnt = 0;
    while (1) { cnt++; if (prv[v] < 0) break; v = prv[v]; }
    if (out->cap < cnt) { out->cap = (int32_t)cnt + 16; out->n = realloc(out->n, out->cap * sizeof(int32_t)); }
    out->len = (int32_t)cnt; v = goal;
    for (int64_t k = cnt - 1; k >= 0; k--) { out->n[k] = v; v = prv[v]; }
    out->pv = pv;
    return 1;
}

/* mark the cells of a cluster (groups of net n with root r, plus routed paths of that cluster) as sources or targets */
static int32_t *cl_of_path;   /* [NC][2] cluster group of each path (group index of its source) */
static void mark_cluster(int n, int r, int as_src, int *bb) {
    for (int64_t q = P->nc_off[n]; q < P->nc_off[n + 1]; q++) {
        int ci = P->nc_list[q];
        int gs[2] = {P->c_ga[ci], P->c_gb[ci]};
        for (int t = 0; t < 2; t++) {
            int g = gs[t]; if (g < 0 || uf_find(g) != r) continue;
            for (int64_t k = P->g_off[g]; k < P->g_off[g + 1]; k++) {
                int32_t v = P->g_cells[k]; int64_t c2 = v % P2; int j = (int)(c2 / P->NX), i = (int)(c2 % P->NX);
                if (as_src) { if (seen[v] != tok_search) { seen[v] = tok_search; gc[v] = 0; prv[v] = -1; hpush(0, v); } }
                else tmark[v] = tok_t;
                if (j < bb[0]) bb[0] = j; if (j > bb[1]) bb[1] = j; if (i < bb[2]) bb[2] = i; if (i > bb[3]) bb[3] = i;
            }
        }
        for (int pp = 0; pp < 2; pp++) {
            Path *p = pp ? &PB[ci] : &PA[ci];
            if (!p->len || uf_find(cl_of_path[2 * ci + pp]) != r) continue;
            for (int32_t k = 0; k < p->len; k++) {
                int32_t v = p->n[k]; int64_t c2 = v % P2; int j = (int)(c2 / P->NX), i = (int)(c2 % P->NX);
                if (as_src) { if (seen[v] != tok_search) { seen[v] = tok_search; gc[v] = 0; prv[v] = -1; hpush(0, v); } }
                else tmark[v] = tok_t;
                if (j < bb[0]) bb[0] = j; if (j > bb[1]) bb[1] = j; if (i < bb[2]) bb[2] = i; if (i > bb[3]) bb[3] = i;
            }
        }
    }
}

/* route one connection (both clusters known); returns 1 when the clusters are joined (or both on the plane) */
static int route_conn(int ci, float pres, int hard, Path *dst, int which) {
    int n = P->c_net[ci];
    int ra = uf_find(P->c_ga[ci]), rb = uf_find(P->c_gb[ci]);
    if (ra == rb) return 2;
    int pl = P->plane[n];
    int src = ra, tgt = rb, pg = 0;
    if (pl) {
        if (gplane[ra] && gplane[rb]) pg = 0;               /* both on the plane already: join them directly */
        else { pg = 1; if (gplane[ra]) { src = rb; tgt = ra; } }
    }
    const int32_t *w = P->win + 4 * n;
    int sb[4] = {1 << 30, -1, 1 << 30, -1}, tb[4] = {1 << 30, -1, 1 << 30, -1};
    tok_search++; tok_t++; hn = 0;
    mark_cluster(n, tgt, 0, tb);
    mark_cluster(n, src, 1, sb);
    if (sb[1] < 0 || (tb[1] < 0 && !pg)) return 0;
    int m = (int)(P->conn_margin / P->grid);
    int okp = 0;
    for (int pass = 0; pass < 2 && !okp; pass++) {
        int bj0, bj1, bi0, bi1;
        if (pass == 0) {
            int lo_j = sb[0] < tb[0] ? sb[0] : tb[0], hi_j = sb[1] > tb[1] ? sb[1] : tb[1];
            int lo_i = sb[2] < tb[2] ? sb[2] : tb[2], hi_i = sb[3] > tb[3] ? sb[3] : tb[3];
            if (tb[1] < 0) { lo_j = sb[0]; hi_j = sb[1]; lo_i = sb[2]; hi_i = sb[3]; }
            bj0 = lo_j - m; bj1 = hi_j + m + 1; bi0 = lo_i - m; bi1 = hi_i + m + 1;
            if (bj0 < w[0]) bj0 = w[0]; if (bj1 > w[1]) bj1 = w[1]; if (bi0 < w[2]) bi0 = w[2]; if (bi1 > w[3]) bi1 = w[3];
        } else {
            bj0 = w[0]; bj1 = w[1]; bi0 = w[2]; bi1 = w[3];
            tok_search++; hn = 0; mark_cluster(n, src, 1, sb);
        }
        okp = astar(n, pres, hard, pg, bj0, bj1, bi0, bi1, tb[1] < 0 ? sb[0] : tb[0], tb[1] < 0 ? sb[1] : tb[1], tb[1] < 0 ? sb[2] : tb[2], tb[1] < 0 ? sb[3] : tb[3], dst);
    }
    if (!okp) return 0;
    cl_of_path[2 * ci + which] = src;
    ownv_collect(dst);
    if (dst->pv) { gplane[src] = 1; return gplane[uf_find(P->c_gb[ci])] && gplane[uf_find(P->c_ga[ci])] ? 1 : 3; }
    /* joined src and tgt */
    int a = uf_find(src), b = uf_find(tgt); int pl2 = gplane[a] | gplane[b];
    uf[a] = b; gplane[b] = pl2;
    return 1;
}

static void reset_net(int n) {
    for (int64_t q = P->nc_off[n]; q < P->nc_off[n + 1]; q++) {
        int ci = P->nc_list[q];
        int gs[2] = {P->c_ga[ci], P->c_gb[ci]};
        for (int t = 0; t < 2; t++) if (gs[t] >= 0) { uf[gs[t]] = gs[t]; gplane[gs[t]] = P->g_onplane[gs[t]]; }
    }
    nownv = 0;
}

static int route_net(int n, float pres, int hard) {
    int fails = 0;
    for (int64_t q = P->nc_off[n]; q < P->nc_off[n + 1]; q++) {
        int ci = P->nc_list[q];
        PA[ci].len = 0; PA[ci].pv = 0; PB[ci].len = 0; PB[ci].pv = 0;
    }
    reset_net(n);
    for (int64_t q = P->nc_off[n]; q < P->nc_off[n + 1]; q++) {
        int ci = P->nc_list[q];
        int r = route_conn(ci, pres, hard, &PA[ci], 0);
        if (r == 3) r = route_conn(ci, pres, hard, &PB[ci], 1);   /* plane net: the other cluster still needs the plane */
        if (r == 3) r = 0;
        P->out_status[ci] = r == 2 ? 2 : (r == 1 ? 1 : 0);
        if (r == 0) fails++;
    }
    return fails;
}

static double now(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec + 1e-9 * t.tv_nsec; }

/* path conflicts with other nets (net not stamped): any node of the path occupied */
static int path_conflicts(int n, const Path *p) {
    for (int32_t k = 0; k < p->len; k++) {
        int32_t v = p->n[k]; int64_t c2 = v % P2;
        int via = (k + 1 < p->len && p->n[k + 1] / P2 != v / P2) || (p->pv && k == p->len - 1);
        if (P->lab[v] != n && ftn(n, c2)[v]) return 1;
        if (via && FV[P->kV[n]][c2]) return 1;
    }
    return 0;
}

int pf_run(PF *p, int32_t *path_out, int64_t cap, int64_t *path_off) {
    P = p; N = (int64_t)p->NL * p->NY * p->NX; P2 = (int64_t)p->NY * p->NX;
    double t0 = now();
    FT = calloc(p->nKT, sizeof(uint8_t *)); FV = calloc(p->nKV, sizeof(uint8_t *));
    for (int k = 0; k < p->nKT; k++) FT[k] = calloc(N, 1);
    for (int k = 0; k < p->nKV; k++) FV[k] = calloc(P2, 1);
    hist = calloc(N, sizeof(float)); histV = calloc(P2, sizeof(float)); gc = malloc(N * sizeof(float));
    prv = malloc(N * sizeof(int32_t)); seen = calloc(N, sizeof(int32_t)); tmark = calloc(N, sizeof(int32_t));
    stampT = calloc(N, sizeof(int32_t)); stampV = calloc(P2, sizeof(int32_t));
    PA = calloc(p->NC, sizeof(Path)); PB = calloc(p->NC, sizeof(Path)); cl_of_path = calloc(2 * p->NC, sizeof(int32_t));
    uf = malloc(p->NG * sizeof(int32_t)); gplane = malloc(p->NG * sizeof(int32_t));
    for (int g = 0; g < p->NG; g++) { uf[g] = g; gplane[g] = p->g_onplane[g]; }
    supp = calloc(N, sizeof(int32_t)); acc = calloc(2 * p->NC, 1); tok_supp = 0; n_dangling = 0;
    int32_t *netfail = calloc(p->NNET + 1, sizeof(int32_t)); int64_t *netover = calloc(p->NNET + 1, sizeof(int64_t));
    int it, last = 0; int64_t over = 0;
    for (it = 0; it < p->max_iter; it++) {
        if (now() - t0 > p->tlim) break;
        float pres = p->pres0 * powf(p->pres_mult, (float)it);
        int nre = 0; nexp_tot = 0;
        for (int q = 0; q < p->NORD; q++) {
            int n = p->order[q];
            if (p->nc_off[n] == p->nc_off[n + 1]) continue;
            if (it >= p->reroute_all && !netfail[n] && !netover[n]) continue;
            if (it > 0) stamp_net(n, -1);
            netfail[n] = route_net(n, pres, 0);
            stamp_net(n, +1); nre++;
        }
        over = 0; int unr = 0;
        for (int n = 1; n <= p->NNET; n++) { netover[n] = net_over(n, 1); over += netover[n]; unr += netfail[n]; }
        float *s = p->it_stats + 6 * it; s[0] = (float)over; s[1] = (float)unr; s[2] = (float)(now() - t0); s[3] = (float)nre; s[4] = (float)(nexp_tot / 1e6); s[5] = pres;
        last = it + 1;
        if (over == 0) break;
    }
    *p->n_iter = last;
    /* legalisation: drop conflicting paths, then re-route the dropped connections with occupied cells blocked */
    for (int n = 1; n <= p->NNET; n++) if (p->nc_off[n] != p->nc_off[n + 1]) stamp_net(n, -1);
    for (int q = 0; q < p->NORD; q++) {
        int n = p->order[q];
        for (int64_t k = p->nc_off[n]; k < p->nc_off[n + 1]; k++) {
            int ci = p->nc_list[k];
            if (path_conflicts(n, &PA[ci]) || path_conflicts(n, &PB[ci])) { PA[ci].len = 0; PA[ci].pv = 0; PB[ci].len = 0; PB[ci].pv = 0; if (p->out_status[ci] == 1) p->out_status[ci] = 3; }
        }
        stamp_net(n, +1);
    }
    {
        /* rebuild cluster state per net and fill the dropped connections greedily */
        for (int q = 0; q < p->NORD; q++) {
            int n = p->order[q]; int need = 0;
            for (int64_t k = p->nc_off[n]; k < p->nc_off[n + 1]; k++) if (p->out_status[p->nc_list[k]] != 1) need = 1;
            if (!need) continue;
            stamp_net(n, -1);
            reset_net(n);
            /* [grow8] a kept path whose start or end lay on a dropped path of its net is dangling now: keep only the paths whose both
               ends sit on the net's end copper or on another kept path (fixpoint), drop the rest and re-route them below.
               Off by default (-DLEGAL_SUPPORT=1 to build it): on the q4 placement it gave 41 unconnected against 34 without it. */
#if LEGAL_SUPPORT
            {
                int32_t tk = ++tok_supp;
                for (int64_t k = p->nc_off[n]; k < p->nc_off[n + 1]; k++) {
                    int ci = p->nc_list[k]; int gs[2] = {p->c_ga[ci], p->c_gb[ci]};
                    for (int t = 0; t < 2; t++) for (int64_t z = p->g_off[gs[t]]; z < p->g_off[gs[t] + 1]; z++) supp[p->g_cells[z]] = tk;
                }
                int ch = 1; int nk = 0;
                for (int64_t k = p->nc_off[n]; k < p->nc_off[n + 1]; k++) { int ci = p->nc_list[k]; acc[2 * ci] = acc[2 * ci + 1] = 0; }
                while (ch) {
                    ch = 0;
                    for (int64_t k = p->nc_off[n]; k < p->nc_off[n + 1]; k++) {
                        int ci = p->nc_list[k];
                        for (int pp = 0; pp < 2; pp++) {
                            Path *pa = pp ? &PB[ci] : &PA[ci];
                            if (!pa->len || acc[2 * ci + pp]) continue;
                            if (supp[pa->n[0]] == tk && (pa->pv || supp[pa->n[pa->len - 1]] == tk)) {
                                acc[2 * ci + pp] = 1; ch = 1; nk++;
                                for (int32_t z = 0; z < pa->len; z++) supp[pa->n[z]] = tk;
                            }
                        }
                    }
                }
                for (int64_t k = p->nc_off[n]; k < p->nc_off[n + 1]; k++) {
                    int ci = p->nc_list[k];
                    if ((PA[ci].len && !acc[2 * ci]) || (PB[ci].len && !acc[2 * ci + 1])) {
                        PA[ci].len = 0; PA[ci].pv = 0; PB[ci].len = 0; PB[ci].pv = 0;
                        if (p->out_status[ci] == 1) p->out_status[ci] = 3;
                        n_dangling++;
                    }
                }
            }
#endif
            for (int64_t k = p->nc_off[n]; k < p->nc_off[n + 1]; k++) {      /* kept paths: replay their joins */
                int ci = p->nc_list[k];
                for (int pp = 0; pp < 2; pp++) {
                    Path *pa = pp ? &PB[ci] : &PA[ci]; if (!pa->len) continue;
                    ownv_collect(pa);
                    if (pa->pv) gplane[uf_find(cl_of_path[2 * ci + pp])] = 1;
                    else { int a = uf_find(p->c_ga[ci]), b = uf_find(p->c_gb[ci]); if (a != b) { int pl2 = gplane[a] | gplane[b]; uf[a] = b; gplane[b] = pl2; } }
                }
            }
            for (int64_t k = p->nc_off[n]; k < p->nc_off[n + 1]; k++) {
                int ci = p->nc_list[k];
                if (p->out_status[ci] == 1) continue;
                PA[ci].len = 0; PB[ci].len = 0; PA[ci].pv = PB[ci].pv = 0;
                int r = route_conn(ci, 0.f, 1, &PA[ci], 0);
                if (r == 3) r = route_conn(ci, 0.f, 1, &PB[ci], 1);
                if (r == 3) r = 0;
                p->out_status[ci] = r == 2 ? 2 : (r == 1 ? 1 : (p->out_status[ci] == 3 ? 3 : 0));
            }
            stamp_net(n, +1);
        }
    }
    int64_t fo = 0;
    for (int n = 1; n <= p->NNET; n++) fo += net_over(n, 0);
    *p->final_over = (int32_t)fo;
    /* output: per connection 2 paths; plane via flagged by a negative sentinel -(node+1) appended */
    int64_t pos = 0;
    for (int ci = 0; ci < p->NC; ci++) {
        for (int pp = 0; pp < 2; pp++) {
            Path *pa = pp ? &PB[ci] : &PA[ci];
            path_off[2 * ci + pp] = pos;
            for (int32_t k = 0; k < pa->len && pos < cap; k++) path_out[pos++] = pa->n[k];
            if (pa->pv && pa->len && pos < cap) path_out[pos++] = -1;
        }
    }
    path_off[2 * p->NC] = pos;
    for (int k = 0; k < p->nKT; k++) free(FT[k]);
    for (int k = 0; k < p->nKV; k++) free(FV[k]);
    free(FT); free(FV); free(hist); free(histV); free(gc); free(prv); free(seen); free(tmark); free(stampT); free(stampV);
    for (int ci = 0; ci < p->NC; ci++) { free(PA[ci].n); free(PB[ci].n); }
    free(supp); free(acc);
    free(PA); free(PB); free(cl_of_path); free(uf); free(gplane); free(netfail); free(netover); free(heap); heap = NULL; hcap = 0; free(ownv); ownv = NULL; capownv = 0;
    return pos >= cap ? -1 : 0;
}
