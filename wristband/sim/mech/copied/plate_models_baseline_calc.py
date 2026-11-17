def navier(a, b, t, E, nu, q=1.0, terms=79):
    D = E * t ** 3 / (12 * (1 - nu ** 2)); w = 0.0; mx = 0.0; my = 0.0
    for m in range(1, terms + 1, 2):
        for n in range(1, terms + 1, 2):
            s = (-1) ** ((m + n) // 2 - 1); den = m * n * (m * m / a ** 2 + n * n / b ** 2) ** 2
            w += s / den; mx += s * (m * m / a ** 2 + nu * n * n / b ** 2) / den; my += s * (nu * m * m / a ** 2 + n * n / b ** 2) / den
    w *= 16 * q / (math.pi ** 6 * D); mx *= 16 * q / math.pi ** 4; my *= 16 * q / math.pi ** 4
    return w, 6 * max(mx, my) / t ** 2
def levy_free_edge(a, b, t, E, nu, q=1.0, terms=61):
    """engineering lens check_mech.py (validated there against Navier): plate simply supported on three edges, FREE on the fourth (y = b);
    deflection at (a/2, b) in mm for q in MPa"""
    D = E * t ** 3 / (12 * (1 - nu ** 2)); w = 0.0; x = a / 2; y = b
    for m in range(1, terms + 1, 2):
        al = m * math.pi / a; wp = 4 * q * a ** 4 / (D * math.pi ** 5 * m ** 5)
        def g(yy):
            e0 = math.exp(-al * yy); s = b - yy; eb = math.exp(-al * s)
            g1 = [e0, -al * e0, al ** 2 * e0, -al ** 3 * e0]
            g2 = [al * yy * e0, al * e0 * (1 - al * yy), -al ** 2 * e0 * (2 - al * yy), al ** 3 * e0 * (3 - al * yy)]
            g3 = [eb, al * eb, al ** 2 * eb, al ** 3 * eb]
            g4 = [al * s * eb, -al * eb * (1 - al * s), -al ** 2 * eb * (2 - al * s), -al ** 3 * eb * (3 - al * s)]
            return [[g1[k], g2[k], g3[k], g4[k]] for k in range(4)]
        G0, Gb = g(0.0), g(b)
