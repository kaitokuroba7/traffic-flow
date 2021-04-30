import numpy as np
import matplotlib.pyplot as plt


# -----------------------------------------------------------------------------
# set computational mesh
def set_mesh():
    dx = (xmax - xmin) / (nx - 1.)
    x = np.linspace(xmin, xmax, nx)
    return x, dx


# -----------------------------------------------------------------------------
# define initial condition
def ic():
    u = np.ones((lmax, nx))
    if (model == 'lwr'):
        u[0, :] *= rho0
    elif (model == 'pw'):
        u[0, :] *= rho0
        u[1, :] *= rho0 * vel(rho0)
    elif (model == 'zhang'):
        u[0, :] *= rho0
        u[1, :] *= 0.
    return u


# -----------------------------------------------------------------------------
# compute step size
def step():
    dt = cfl * dx / maxlam(u)
    return dt


# -----------------------------------------------------------------------------
# solver
def solver():
    global u, res
    if (method == 'maccormack'):
        for stage in range(0, 2):
            e = flux(stage)
            res = residual(e)
            if (stage == 0):
                u_old = np.copy(u)
                u += dt * res
            elif (stage == 1):
                u = .5 * (u + u_old + dt * res)
    elif (method == 'rk4'):
        alpha = [1. / 4, 1. / 3, 1. / 2, 1.]
        u_old = np.copy(u)
        for stage in range(0, 4):
            e = flux()
            res = residual(e)
            u = u_old + alpha[stage] * dt * res
    elif (method == 'beam-warming'):
        e = flux()
        res = residual(e)
        # Thomas algorithm
        ci = np.zeros(nx - 1)
        ci[0] = .25 * dt / dx * aa(u[:, 1])
        for i in range(1, nx - 2):
            ci[i] = (.25 * dt / dx * aa(u[:, i + 1])) / (1 - \
                                                         (-.25 * dt / dx * aa(u[:, i - 1]) * ci[i - 1]))
        di = np.zeros(nx)
        di[0] = dt * res[:, 0]
        for i in range(1, nx - 1):
            di[i] = (dt * res[:, i] - \
                     (-.25 * dt / dx * aa(u[:, i - 1])) * di[i - 1]) / (1 - \
                                                                        (-.25 * dt / dx * aa(u[:, i - 1])) * ci[i - 1])
        di[-1] = (- .25 * dt / dx * aa(u[:, -2]) * di[-2]) / \
                 (1 - .25 * dt / dx * aa(u[:, -1]) * ci[-1])
        du = np.zeros(nx)
        du[-1] = di[-1]
        for i in range(nx - 2, -1, -1):
            du[i] += di[i] - ci[i] * du[i + 1]
        u += du
    else:
        e = flux()
        res = residual(e)
        u += dt * res
    return


# -----------------------------------------------------------------------------
# compute maximum eigenvalue of Jacobi matrix
def maxlam(u):
    lam = 0.
    for i in range(0, nx):
        if (model == 'lwr'):
            lam = max(lam, abs(vel(u[0, i])))
        elif (model == 'pw'):
            lam = max(lam, abs(u[1, i] / u[0, i]) + c0)
        elif (model == 'zhang'):
            vi = u[1, i] / u[0, i] + vel(u[0, i])
            lam = max(lam, abs(vi), abs(vi + u[0, i] * (-k)))
    return lam


# -----------------------------------------------------------------------------
# model for velocity
def vel(rho):
    if (state == 'greenshield'):
        v = 1 - k * rho
    elif (state == 'greenberg'):
        vmax = 10.
        if (rho < 1 / np.exp(vmax)):
            v = vmax
        else:
            v = min(vmax, np.log(1 / rho))
    elif (state == 'underwood'):
        v = np.exp(-rho)
    return v


# -----------------------------------------------------------------------------
# flux vector at a single grid point
def ee(ui):
    if (model == 'lwr'):
        vi = vel(ui)
        ei = ui * vi
    elif (model == 'pw'):
        rhoi = ui[0]
        vi = ui[1] / ui[0]
        ei = np.array([rhoi * vi, rhoi * vi ** 2 + c0 ** 2 * rhoi])
    elif (model == 'zhang'):
        rhoi = ui[0]
        mi = ui[1]
        ei = np.array([mi + rhoi * vel(rhoi), mi ** 2 / rhoi + mi * vel(rhoi)])
    return ei


# -----------------------------------------------------------------------------
# Jacobi matrix A at a single grid point
def aa(ui):
    if (model == 'lwr'):
        vi = vel(ui)
        ai = vi
    elif (model == 'pw'):
        vi = ui[1] / ui[0]
        ai = np.array([[0, 1], [c0 ** 2 - vi ** 2, 2 * vi]])
    elif (model == 'zhang'):
        rhoi = ui[0]
        mi = ui[1]
        ai = np.array([[rhoi * (-k) + vel(rhoi), 1], \
                       [-mi ** 2 / rhoi ** 2 + mi * (-k), 2 * mi / rhoi + vel(rhoi)]])
    return ai


# -----------------------------------------------------------------------------
# modal matrix T
def tt(ui):
    if (model == 'pw'):
        vi = ui[1] / ui[0]
        ti = np.array([[1, 1], [vi + c0, vi - c0]])
    elif (model == 'zhang'):
        rhoi = ui[0]
        vi = ui[1] / rhoi + vel(rhoi)
        ti = np.array([[1, 1], [vi - vel(rhoi) - rhoi * (-k), vi - vel(rhoi)]])
    return ti


# -----------------------------------------------------------------------------
# Roe-averaging (evalution of interfacial face)
def roe_avg(u1, u2):
    rho1 = max(u1[0], 1e-3)
    rho2 = max(u2[0], 1e-3)
    R = np.sqrt(rho2 / rho1) if (rho1 >= 0 and rho2 >= 0) else 0
    avgrho = R * rho1
    if (model == 'pw'):
        v1 = min(u1[1] / u1[0], 10.)
        v2 = min(u2[1] / u2[0], 10.)
        avgv = (R * v2 + v1) / (R + 1)
        avgu = [avgrho, avgrho * avgv]
        avglam = np.array([avgv + c0, avgv - c0])
    elif (model == 'zhang'):
        v1 = u1[1] / rho1 + vel(rho1)
        v2 = u2[1] / rho2 + vel(rho2)
        avgv = (R * v2 + v1) / (R + 1)
        avgu = [avgrho, avgrho * (avgv - vel(avgrho))]
        avglam = np.array([avgv, avgv + avgrho * (-k)])
    avgt = tt(avgu)
    avgsig = np.sign(avglam)
    delta = np.dot(np.linalg.inv(avgt), u2 - u1)
    return (delta, avglam, avgt, avgsig)


# -----------------------------------------------------------------------------
# flux vector
def flux(stage=0):
    e = np.zeros((lmax, nx - 1))
    for i in range(0, nx - 1):
        # Lax method
        if (method == 'lax'):
            e1 = ee(u[:, i])
            e2 = ee(u[:, i + 1])
            e[:, i] = .5 * (e1 + e2) - .5 * dx / dt * (u[:, i + 1] - u[:, i])
        # Lax-Wendroff method
        elif (method == 'lax-wendroff'):
            e1 = ee(u[:, i])
            e2 = ee(u[:, i + 1])
            a1 = aa(u[:, i])
            a2 = aa(u[:, i + 1])
            a = .5 * (a1 + a2)
            e[:, i] = .5 * (e1 + e2) - .5 * dt / dx * np.dot(a, e2 - e1)
        # MacCormack method
        elif (method == 'maccormack'):
            if (stage == 0):
                e[:, i] = ee(u[:, i + 1])
            elif (stage == 1):
                e[:, i] = ee(u[:, i])
        # Jameson 4-stage Runga-Kutta
        elif (method == 'rk4'):
            e1 = ee(u[:, i])
            e2 = ee(u[:, i + 1])
            e[:, i] = .5 * (e1 + e2)
        # Beam & Warming method
        elif (method == 'beam-warming'):
            e1 = ee(u[:, i])
            e2 = ee(u[:, i + 1])
            e[:, i] = .5 * (e1 + e2)
        # Steger & Warming flux vetcor splitting
        elif (method == 'steger-warming'):
            if (model == 'pw'):
                v1 = u[1, i] / u[0, i]
                v2 = u[1, i + 1] / u[0, i + 1]
                lam1_p = max(v1 + c0, 0)
                lam2_p = max(v1 - c0, 0)
                lam1_m = min(v2 + c0, 0)
                lam2_m = min(v2 - c0, 0)
            elif (model == 'zhang'):
                rho1 = u[0, i]
                rho2 = u[0, i + 1]
                v1 = u[1, i] / rho1 + vel(rho1)
                v2 = u[1, i + 1] / rho2 + vel(rho2)
                lam1_p = max(v1, 0)
                lam2_p = max(v1 + rho1 * (-k), 0)
                lam1_m = min(v2, 0)
                lam2_m = min(v2 + rho2 * (-k), 0)
            Lam_p = np.array([[lam1_p, 0], [0, lam2_p]])
            Lam_m = np.array([[lam1_m, 0], [0, lam2_m]])
            a_p = np.dot(tt(u[:, i]), Lam_p, np.linalg.inv(tt(u[:, i])))
            a_m = np.dot(tt(u[:, i + 1]), Lam_m, np.linalg.inv(tt(u[:, i + 1])))
            e_p = np.dot(a_p, u[:, i])
            e_m = np.dot(a_m, u[:, i + 1])
            e[:, i] = e_p + e_m
        # Roe's approximate Riemann solver
        elif (method == 'roe'):
            e1 = ee(u[:, i])
            e2 = ee(u[:, i + 1])
            (delta, avglam, avgt, avgsig) = roe_avg(u[:, i], u[:, i + 1])
            e[:, i] = .5 * (e1 + e2)
            for l in range(0, lmax):
                e[:, i] -= .5 * delta[l] * abs(avglam[l]) * avgt[:, l]
        # TVD method
        elif (method[:3] == 'tvd'):
            e1 = ee(u[:, i])
            e2 = ee(u[:, i + 1])

            e[:, i] = .5 * (e1 + e2)
            if (i > 0 and i < nx - 2):
                (delta, avglam, avgt, avgsig) = \
                    roe_avg(u[:, i], u[:, i + 1])
                (delta1, avglam1, avgt1, avgsig1) = \
                    roe_avg(u[:, i - 1], u[:, i])
                (delta2, avglam2, avgt2, avgsig2) = \
                    roe_avg(u[:, i + 1], u[:, i + 2])
                for l in range(0, lmax):
                    if (avgsig[l] > 0):
                        r = 1e2 if (delta[l] == 0) else delta1[l] / delta[l]
                    else:
                        r = 1e2 if (delta[l] == 0) else delta2[l] / delta[l]
                    # Roe superbee limiter
                    if (method == 'tvd-superbee'):
                        phi = max(0, min(1, 2 * r), min(r, 2))
                    elif (method == 'tvd-vanleer'):
                        phi = (r + abs(r)) / (1 + abs(r))
                    e[:, i] -= .5 * (avgsig[l] + phi * (avglam[l] * dt / dx \
                                                        - avgsig[l])) * delta[l] * abs(avglam[l]) * avgt[:, l]

    # artificial viscosity
    if (avmodel): e = av(e)
    return e


# -----------------------------------------------------------------------------
# source vector
def source(u):
    s = np.zeros((lmax, nx))
    tau = 1.
    for i in range(0, nx):
        rhoi = u[0, i]
        vi = u[1, i] / u[0, i]
        s[0, i] = 0.
        s[1, i] = rhoi * (vel(rhoi) - vi) / tau
    return s


# -----------------------------------------------------------------------------
# residual
def residual(e):
    res = np.zeros((lmax, nx))
    for i in range(1, nx - 1):
        res[:, i] = -(e[:, i] - e[:, i - 1]) / dx
    if (model == 'pw'): res += source(u)
    return res


# -----------------------------------------------------------------------------
# artificial viscosity
def av(e):
    # Von-Neumann & Ritchmyer
    lam0 = maxlam(u)
    u0 = .5
    for i in range(1, nx - 2):
        du = u[:, i + 1] - u[:, i]
        d3u = u[:, i + 2] - 3 * u[:, i + 1] + 3 * u[:, i] - u[:, i - 1]
        eps2 = kappa2 * abs(du) / u0
        eps4 = kappa4
        e[:, i] -= (eps2 * du - eps4 * d3u) * lam0
    return e


# -----------------------------------------------------------------------------
# determine the order of given method
def get_order(method):
    order = {'lax': 1,
             'lax-wendroff': 2,
             'maccormack': 2,
             'rk4': 2,
             'beam-warming': 2,
             'steger-warming': 1,
             'roe': 1,
             'tvd-superbee': 2,
             'tvd-vanleer': 2}
    return order[method]


# -----------------------------------------------------------------------------
# parameters
xmin = 0
xmax = 200
nx = 151  # number of grid points

rho0 = 0.3
fr = 0.5
cfl = 0.5
imax = 800
eps = 1e-5
tmax = 50
k = 0.9  # for Greenshield model
c0 = 0.5  # for PW model

# -----------------------------------------------------------------------------
# traffic flow model
# acceptable values:
## lwr   (Lighthill-Whitham-Richards model)
## pw    (Payne-Whitham model)
## zhang (Zhang model)
model = 'lwr'
lmax = 1 if (model == 'lwr') else 2

# relationship between density and speed
# acceptable values: greenshield, greenberg, underwood
state = 'greenshield'

# -----------------------------------------------------------------------------
# numerical methods
# acceptable values:
## lax, lax-wendroff, maccormack, beam-warming, steger-warming
## rk4, roe, tvd-superbee, tvd-vanleer
method = 'beam-warming'

avmodel = True
kappa2 = .2
kappa4 = 0.02

# turn off AV model for first-order schemes
order = get_order(method)
if (order == 1): avmodel = False

# grid points
(x, dx) = set_mesh()
# initial condition
u = ic()

fig = plt.figure()
ax = fig.add_subplot(111)

time = 0
for i in range(0, imax):
    # step size
    dt = step()

    solver()

    # maxres = max(abs(res[0,]))
    # if (maxres < 1e-5): break
    time += dt
    if time < tmax * fr:
        color = 'r'
        if model == 'lwr':
            u[0, nx / 2] = 1.
            # u[0,nx/2]   = 0.
        elif model == 'pw':
            u[0, nx / 2] = 1.
            u[1, nx / 2] = u[0, nx / 2] * vel(u[0, nx / 2])
        elif model == 'zhang':
            u[0, nx / 2] = 1.
            u[1, nx / 2] = 0.
    else:
        color = 'g'
        if model == 'lwr':
            u[0, nx / 2] = rho0
            # u[0,nx/2]   = rho0
        elif model == 'pw':
            u[0, nx / 2] = rho0
            u[1, nx / 2] = u[0, nx / 2] * vel(u[0, nx / 2])
        elif model == 'zhang':
            u[0, nx / 2] = rho0
            u[1, nx / 2] = 0.
    u[:, 0] = u[:, 1]
    u[:, -1] = u[:, -2]

    if time > tmax: time = 0

    if i == 0:
        line1, = ax.plot(x, u[0,], '-o')
        line1.set_color(color)
        ax.set_ylim(0, 1)
        fig.show()
    else:
        line1.set_ydata(u[0,])
        line1.set_color(color)
        fig.canvas.draw()
