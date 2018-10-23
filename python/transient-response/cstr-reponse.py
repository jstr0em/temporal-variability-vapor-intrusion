import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import LSODA
from scipy.interpolate import interp1d
import sqlite3
import pandas as pd
import plotly.graph_objs as go
import plotly.offline as py
import plotly.io as pio

data_dir = './data/preferential-pathway-sensitivity/'
figures_dir = './figures/transient-response/'

def process_data(data):
    data.n *= 3600.0 # converts mol/s to mol/hr
    n_func = interp1d(data.p.values, data.n.values) # interpolation function
    # all possible pressures and air exchanges rates
    ps = np.arange(-10,11)
    Aes = np.arange(0.1, 1.6, 0.1)
    # calculates the indoor air concentration and puts all the input variables
    # and concentration into lists
    p, Ae, c, n = [], [], [], []
    for Ae_now in Aes:
        for p_now in ps:
                Ae.append(Ae_now)
                p.append(p_now)
                c.append(n_func(p_now)/V/Ae_now)
                n.append(n_func(p_now))
    # puts data into dataframe
    df = pd.DataFrame(
        {
        'p': p,
        'Ae': Ae,
        'c': c,
        'n': n,
        }
    )
    # reference state
    ref_state = ((df.p == -2) & (df.Ae == 0.1))
    ref = df[ref_state].copy()
    # potential target states
    target_state = ((ref.c.values/df.c >= 10.0) | (ref.c.values/df.c <= 0.1)) & (df.p % 5 == 0) & (df.p != 0) & (df.Ae == 1.0)
    target = df[target_state].copy()
    return df, ref, target

def plot_contour(df, ref, target):
    # data to plot
    data = [
        go.Contour(
            z=df.c.apply(np.log10),
            x=df.p,
            y=df.Ae,
        ),
        go.Scatter(
            x = ref.p,
            y = ref.Ae
        ),
        go.Scatter(
            x = target.p,
            y = target.Ae,
            mode = 'markers',
        ),
    ]
    # figure
    fig = go.Figure(
        data=data,
        #layout=layout,
    )
    # saving data
    filename = 'p-ae-contour'
    pio.write_image(
        fig,
        file = figures_dir + filename + '.pdf',
        )
    return



def solve_cstr(data):
    # unsteady cstr method
    def dudt(t, u):
        dudt =  n/V - u*Ae
        return dudt
    #retrives processed data
    df, ref, target = process_data(data)
    # time variables
    t0 = 0.0 # initial time
    tau = 128 # max allowed time
    # initial/reference concentration
    y0 = ref.n/V/ref.Ae
    for n, Ae, p in zip(target.n, target.Ae, target.p):
        # solving for target state change in variable values
        print('Case: p = %1.1f, Ae = %1.1f' % (p, Ae))
        c = n/V/Ae
        solver = LSODA(
            dudt,
            t0,
            y0.values,
            tau,
            max_step=1.0,
        )
        t, y = [], [] # storage lists
        while solver.y > 1.01*c:
            t.append(solver.t)
            y.append(solver.y)
            try:
                solver.step()
            except:
                print('Solver failed in first loop at t = %1.1f' % solver.t)
                break
        t_eq = solver.t
        print('Min. reached after %2.1f hours' % t_eq)
        # going back to reference state variables
        Ae_label = Ae
        Ae = ref.Ae.values
        while solver.y < 0.99*y0.values:
            t.append(solver.t)
            y.append(solver.y)
            try:
                solver.step()
            except:
                print('Solver failed in second loop at t = %1.1f' % solver.t)
                break
        t_org = solver.t
        print('Max. reached after %2.1f hours' % t_org)

        plt.semilogy(
            np.array(t),
            y,
            label='p = %i, Ae = %1.1f' % (p, Ae_label),
        )

    plt.legend()
    plt.show()
    return


def plot_ribbon(data):

    df, ref, target = process_data(data)


    traces = []


    traces.append(
        dict(
            x=df.p.values,
            y=df.Ae.values,
            z=df.n.values/df.Ae.values/V,
            type='surface',
            showscale=False,
        )
    )
    """
    y_raw = spectra[:, 0] # wavelength
    sample_size = df.shape[1]-1
    for i in range(1, sample_size):
        z_raw = spectra[:, i]
        x = []
        y = []
        z = []
        ci = int(255/sample_size*i) # ci = "color index"
        for j in range(0, len(z_raw)):
            z.append([z_raw[j], z_raw[j]])
            y.append([y_raw[j], y_raw[j]])
            x.append([i*2, i*2+1])
        traces.append(dict(
            z=z,
            x=x,
            y=y,
            colorscale=[ [i, 'rgb(%d,%d,255)'%(ci, ci)] for i in np.arange(0,1.1,0.1) ],
            showscale=False,
            type='surface',
        ))
    """
    # figure
    fig = go.Figure(
        data=traces,
        #layout=layout,
    )
    # saving data
    filename = 'p-ae-ribbon'
    pio.write_image(
        fig,
        file = figures_dir + filename + '.svg',
        )
    return


# parameters
V = 200.0

# reads data file
data = pd.read_csv(
    data_dir + 'param-no-preferential-pathway.csv',
    header=4,
)
# only interested in the case with a gravel sub-base and no contaminant in the
# pp
data = data[(data.SB == 1) & (data.chi == 0)]
#solve_cstr(data)
plot_ribbon(data)
