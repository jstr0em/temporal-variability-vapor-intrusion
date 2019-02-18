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

# parameters
V = 200.0
#df = pd.read_csv('./data/soils/all-data.csv') # no PP data

# pp data stuff
df = pd.read_csv('./data/preferential-pathway-sensitivity/param-preferential-pathway.csv', header=4) # PP data (only 1 soil)
df['soil_type'] = np.repeat('sandy-clay',len(df))
df = df[ (df['SB']==1) & (df['chi']==1) ]

Ae = 0.5
t1, t2 = [], []
dc1, dc2 = [], []
Aes = []
dcdt1, dcdt2 = [], []
soils = []
c_max, c_min = [], []

df.n *= 3600.0
for Ae in [0.5, 1.0, 1.5]:
    for soil in df['soil_type'].unique():
        ref = df[ (df['soil_type'] == soil) & ( df.p==-0.5 ) ]
        target = df[ (df['soil_type'] == soil) & ( df.p==0.5 ) ]
        Aes.append(Ae)
        soils.append(soil)
        # unsteady cstr method
        def dudt(t, u):
            dudt =  n/V - u*Ae
            return dudt
        #retrives processed data
        # time variables
        t0 = 0.0 # initial time
        tau = 240 # max allowed time
        # initial/reference concentration
        y0 = ref.n/V/Ae
        print(y0)
        c_max.append(y0.values[0])
        for n, p in zip(target.n.values, target.p.values):
            # solving for target state change in variable values
            #print('Case: p = %1.1f, Ae = %1.1f' % (p, Ae))
            c = n/V/Ae
            c_min.append(c)
            solver = LSODA(
                dudt,
                t0,
                y0.values,
                tau,
                max_step=0.1,
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
            t1.append(t_eq)
            dc1.append(abs(float(c-y0)))
            dcdt1.append(float((c-y0)/t_eq))
            print('Min. reached after %2.1f hours' % t_eq)
            # going back to reference state variables
            n = ref.n
            while solver.y < 0.99*y0.values:
                t.append(solver.t)
                y.append(solver.y)
                try:
                    solver.step()
                except:
                    print('Solver failed in second loop at t = %1.1f' % solver.t)
                    break
            t_org = solver.t - t_eq
            t2.append(t_org)
            dc2.append(abs(float(y0-c)))
            dcdt2.append(float((y0-c)/t_org))
            print('Max. reached after %2.1f hours' % t_org)

down  = pd.DataFrame({
    'soil': soils,
    'Ae': Aes,
    't': t1,
    'dc': dc1,
    'dcdt': dcdt1,
})

up = pd.DataFrame({
    'soil': soils,
    'Ae': Aes,
    't': t2,
    'dc': dc2,
    'dcdt': dcdt2,
})

both = pd.DataFrame({
    'Soil': soils,
    'Ae': Aes,
    'TimeDown': t1,
    'TimeUp': t2,
    'Cmax': c_max,
    'Cmin': c_min,
}).to_csv('./data/transient-response/cstr-changes-pp.csv',index=False)

# relationship between t and dc figure
"""

# relationship between soil and t figure

fig, ax = plt.subplots()

down.pivot_table(
    index='soil',
    columns='Ae',
).plot(
    y='t',
    ax=ax,
    rot=45,
)

up.pivot_table(
    index='soil',
    columns='Ae',
).plot(
    y='t',
    ax=ax,
    rot=45,
    style='--',
)


xlabels = []
for str in down.soil.unique():
    xlabels.append(str.title())


ax.set_xticks(np.arange(0,len(xlabels)))
ax.set_xticklabels(xlabels)
ax.set_ylabel('Time to equilibrium (hr)')

ax.legend(title='$A_e$ (1/hr)')

plt.show()
"""