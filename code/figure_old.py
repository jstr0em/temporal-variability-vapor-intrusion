import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.gridspec as gridspec
from scipy import stats
from get_simulation_data import Soil, PreferentialPathway
import datetime
plt.style.use('seaborn')
"""
This figure shows a case (North Island NAS) where indoor/outdoor pressure
difference the key driver at a VI site, and how are are able to model this
by assuming a permeable soil type (sand).
"""
class PressureKDE:
    def __init__(self,y_data_log=False , norm_conc=True):
        nas = pd.read_csv('./data/north_island.csv').dropna()
        asu = pd.read_csv('./data/asu_house.csv').dropna()
        asu_open = asu.loc[asu['Phase']=='Open']
        asu_closed = asu.loc[asu['Phase']=='Closed']


        x='IndoorOutdoorPressure'

        if y_data_log is True:
            y='logIndoorConcentration'
        else:
            y='IndoorConcentration'


        datasets = (nas, asu_open, asu_closed,)
        labels = ('North Island NAS', 'ASU house, PP open', 'ASU house, PP closed',)

        fig, ax = plt.subplots()

        for data, label in zip(datasets, labels):
            if norm_conc is True:
                if y_data_log is True:
                    data2 = data[y]-data[y].mean()
                else:
                    data2 = data[y]/data[y].mean()

            else:
                data2 = data[y]


            r, p = stats.pearsonr(data[x], data2)

            print(label)
            print(data[x].describe(percentiles=[0.05,0.95]), data['IndoorConcentration'].describe(percentiles=[0.05,0.95]), data2.describe(percentiles=[0.05,0.95]))
            sns.kdeplot(
                data=data[x],
                data2=data2,
                shade_lowest=False,
                shade=True,
                label=label + ', r = %1.2f' % r,
                ax=ax,
            )



        yticks, yticklabels = get_log_ticks(-1, 1.5)
        # formatting options
        ax.set(
            xlim=[-30,15],
            ylim=[-1,1.5],
            xlabel='$p_\\mathrm{in/out} \\; \\mathrm{(Pa)}$',
            ylabel='$c_\\mathrm{in}/c_\\mathrm{in,mean}$',
            title='Relationship between indoor/outdoor pressure difference and\nTCE in indoor air (normalized to dataset mean concentration)',
            #yscale='log',
            yticks=yticks,
            yticklabels=yticklabels,
        )
        plt.legend(loc='upper left')
        plt.savefig('./figures/2d_kde/nas_asu_pp.pdf', dpi=300)
        plt.savefig('./figures/2d_kde/nas_asu_pp.png', dpi=300)

        plt.show()

        return


def get_log_ticks(start, stop, style='e'):

    def smart_strip(str):
        for i, x in enumerate(str):
            str[i] = x.rstrip('0')
            if str[i][-1] == '.':

                str[i] += '0'

        return str
    ticks = np.array([])
    ints = np.arange(np.floor(start),np.ceil(stop)+1)
    for int_now in ints:
        ticks = np.append(ticks, np.arange(0.1,1.0,0.1)*10.0**int_now)
        #ticks = np.unique(ticks)
    ticks = np.append(ticks, 1.0*10.0**ints[-1])

    if style=='e':
        labels = ['%1.1e' % tick for tick in ticks]
        ticks_to_keep = ['%1.1e' % 10**int for int in ints]
    elif style=='f':
        labels = ['%1.12f' % tick for tick in ticks]
        ticks_to_keep = ['%1.12f' % 10**int for int in ints]

    ticks_to_keep = np.unique(ticks_to_keep)

    ticks = np.log10(ticks)


    for i, label in enumerate(labels):

        if label in ticks_to_keep:
            #print('Not removing label')
            continue
        else:
            #print('Removing label')
            labels[i] = ' '

    labels = smart_strip(labels)
    return ticks, labels


class AttenuationSubslab:
    def __init__(self):
        asu = pd.read_csv('./data/asu_house.csv')
        asu = asu.loc[asu['Phase']!='CPM']

        ax = sns.boxplot(
            x="Phase",
            y="logAttenuationSubslab",
            data=asu,
            whis=10,
            )


        ticks, labels = get_log_ticks(-3,2, style='f')
        ax.set(
            xlabel='Preferential pathway status',
            ylabel='Attenuation from subslab',
            yticks=ticks,
            yticklabels=labels,
        )

        plt.tight_layout()
        plt.savefig('./figures/temporal_variability/asu_attenuation_subslab.pdf', dpi=300)
        plt.savefig('./figures/temporal_variability/asu_attenuation_subslab.png', dpi=300)

        plt.show()
        return


class Modeling:
    def __init__(self):
        sim = PreferentialPathway().data
        asu = pd.read_csv('../data/asu_house.csv')
        #print(asu['AirExchangeRate'].describe(percentiles=[0.1, 0.9]))
        asu = asu.loc[ (asu['Phase']!='CPM') ]


        # isolates the Ae = 0.5 case for the uniform soil modeling
        sim_data_to_remove = [
            (sim['Simulation']=='Pp Uniform') &
            (
                (sim['AirExchangeRate'] < 0.45) |
                (sim['AirExchangeRate'] > 0.55)
            )
        ]

        sim_data_to_remove = np.invert(sim_data_to_remove)
        sim = sim[sim_data_to_remove[0]]

        p_vals = sim['IndoorOutdoorPressure'].unique()
        Ae = asu['AirExchangeRate'].describe(percentiles=[0.05,0.1,0.9,0.95])


        Ae_low = Ae['5%']
        Ae_high = Ae['95%']

        print(Ae_low, Ae_high)

        from scipy.interpolate import interp2d

        for simulation in ['Pp', 'No Pp']:
            interp_func = interp2d(
                sim.loc[sim['Simulation']==simulation]['IndoorOutdoorPressure'],
                sim.loc[sim['Simulation']==simulation]['AirExchangeRate'],
                sim.loc[sim['Simulation']==simulation]['logAttenuationGroundwater'],
            )
            for Ae_now in [Ae_low, Ae_high]:
                new_sim_vals = pd.DataFrame({
                    'IndoorOutdoorPressure': p_vals,
                    'AirExchangeRate': np.repeat(Ae_now, len(p_vals)),
                    'Simulation': np.repeat(simulation, len(p_vals)),
                    'logAttenuationGroundwater': interp_func(p_vals, Ae_now),
                })
                sim = sim.append(new_sim_vals, ignore_index=True, sort=False)

        fig, (ax1,ax2) = plt.subplots(2,1, sharex=True, sharey=True, figsize=[6.4, 6.4], dpi=300)

        pp_max = sim.loc[(sim['Simulation']=='Pp')&(sim['AirExchangeRate']==Ae_low)]
        pp = sim.loc[(sim['Simulation']=='Pp')&(sim['AirExchangeRate']==0.5)]
        pp_min = sim.loc[(sim['Simulation']=='Pp')&(sim['AirExchangeRate']==Ae_high)]


        ax1.plot(pp['IndoorOutdoorPressure'], pp['logAttenuationGroundwater'],label='Gravel sub-base')
        ax1.fill_between(pp['IndoorOutdoorPressure'], pp_min['logAttenuationGroundwater'], pp_max['logAttenuationGroundwater'],alpha=0.5)

        # ax1
        sns.regplot(
            data=asu.loc[asu['Phase']=='Open'],
            x='IndoorOutdoorPressure',
            y='logAttenuationAvgGroundwater',
            ax=ax1,
            fit_reg=False,
            x_bins=np.linspace(-5,5,40),
            ci=95, # 95% confidence interval
            label='Data',
            color=sns.color_palette()[0]
        )
        sns.lineplot(
            data=sim.loc[sim['Simulation']=='Pp Uniform'],
            x='IndoorOutdoorPressure',
            y='logAttenuationGroundwater',
            ax=ax1,
            label='No gravel sub-base',
        )
        sns.lineplot(
            data=sim.loc[sim['Simulation']=='Pp Uncontaminated'],
            x='IndoorOutdoorPressure',
            y='logAttenuationGroundwater',
            ax=ax1,
            label='Gravel sub-base & clean air in pathway'
        )


        no_pp_max = sim.loc[(sim['Simulation']=='No Pp')&(sim['AirExchangeRate']==Ae_low)]
        no_pp = sim.loc[(sim['Simulation']=='No Pp')&(sim['AirExchangeRate']==0.5)]
        no_pp_min = sim.loc[(sim['Simulation']=='No Pp')&(sim['AirExchangeRate']==Ae_high)]

        ax2.plot(no_pp['IndoorOutdoorPressure'], no_pp['logAttenuationGroundwater'], label='Gravel sub-base')
        ax2.fill_between(no_pp['IndoorOutdoorPressure'], no_pp_min['logAttenuationGroundwater'], no_pp_max['logAttenuationGroundwater'],alpha=0.5)

        # ax2
        sns.regplot(
            data=asu.loc[asu['Phase']=='Closed'],
            x='IndoorOutdoorPressure',
            y='logAttenuationAvgGroundwater',
            ax=ax2,
            fit_reg=False,
            x_bins=np.linspace(-5,5,40),
            ci='sd',
            label='Data',
            color=sns.color_palette()[0],
        )

        ticks, labels = get_log_ticks(-7,-3.5)

        ax1.set(
            xlabel='',
            ylabel='$\\alpha_\\mathrm{gw}$',
            title='Preferential pathway open',
            xlim=[-5,5],
            yticks=ticks,
            yticklabels=labels,
        )


        ax2.set(
            xlabel='$p_\\mathrm{in/out} \; \\mathrm{(Pa)}$',
            ylabel='$\\alpha_\\mathrm{gw}$',
            title='Preferential pathway closed',
            xlim=[-5,5],
            yticks=ticks,
            yticklabels=labels,
        )
        ax1.grid(False)
        ax2.grid(False)

        plt.tight_layout()
        ax1.legend(loc='best')
        ax2.legend(loc='best')
        #plt.savefig('./figures/simulation_predictions/land_drain_scenarios_combo.pdf')
        #plt.savefig('./figures/simulation_predictions/land_drain_scenarios_combo.png')


        return

class IndianapolisTime:
    def __init__(self):
        data = pd.read_csv('./data/indianapolis.csv')
        data['Time'] = data['Time'].apply(pd.to_datetime)
        data.sort_values(by='Time')

        fig, ax = plt.subplots(dpi=300)

        sns.lineplot(
            data=data[data['Specie']=='Trichloroethene'],
            x='Time',
            y='IndoorConcentration',
            ax=ax,
        )


        ax.set_yscale('log')

        start_date, stop_date = datetime.date(2011, 8, 11), datetime.date(2011, 10, 15)

        custom_tick_locs = np.arange(start_date, stop_date, np.timedelta64(1,'W'))
        ax.set(
            title='Indoor TCE concentration at the Indianapolis site',
            ylabel='$c_\\mathrm{in} \; \\mathrm{(\\mu g/m^3)}$',
            xticks=custom_tick_locs,
            xticklabels=custom_tick_locs,
            xlim=([start_date, stop_date]),
        )
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig('./figures/temporal_variability/time_indianapolis.png')
        plt.savefig('./figures/temporal_variability/time_indianapolis.pdf')

        plt.show()
        return

class AirExchangeRateKDE:
    def __init__(self):

        data = pd.read_csv('../data/asu_house.csv').dropna()
        data = data.loc[data['Phase']!='CPM']

        # calculates median indoor/outdoor pressure difference and air exchange rate
        # for each season (for later annotation)
        seasons = []
        ps = []
        Aes = []
        for season in data['Season'].unique():
            analysis = data.loc[data['Season']==season][['IndoorOutdoorPressure','AirExchangeRate']].describe(percentiles=[0.1,0.9])
            seasons.append(season)
            ps.append(analysis['IndoorOutdoorPressure']['50%'])
            Aes.append(analysis['AirExchangeRate']['50%'])


        seasonal_medians = pd.DataFrame({'Season': seasons, 'IndoorOutdoorPressure': ps, 'AirExchangeRate': Aes})





        fig, ax = plt.subplots(dpi=300)
        sns.kdeplot(
            data=data['IndoorOutdoorPressure'],
            data2=data['AirExchangeRate'],
            shade_lowest=False,
            shade=True,
        )


        for season, p, Ae in zip(seasons, ps, Aes):
            ax.annotate(
                season,
                xy=(p,Ae),
                xytext=(p*5,Ae+0.6),
                arrowprops=dict(facecolor='black', shrink=0.001),
            )

        ax.set(
            title='2D KDE showing distributions and relationship between\nindoor/outdoor pressure and air exchange rate',
            ylabel='$A_e \; \\mathrm{(1/hr)}$',
            xlabel='$p_\\mathrm{in/out} \; \\mathrm{(Pa)}$',
            ylim=[0,1.75],
            xlim=[-5,5],
        )



        plt.tight_layout()
        #plt.savefig('./figures/2d_kde/pressure_air_exchange_rate.png')
        #plt.savefig('./figures/2d_kde/pressure_air_exchange_rate.pdf')


        return

class Diurnal:
    def __init__(self):
        from scipy.interpolate import CubicSpline
        path = '../data/diurnal/simulation_results/'

        p_diurnal = pd.read_csv('../data/diurnal/pressure.csv')
        ae_diurnal = pd.read_csv('../data/diurnal/air_exchange_rate.csv')
        pp_closed_const_ae = pd.read_csv(path+'pp_closed_const_ae.csv',header=4)
        pp_closed = pd.read_csv(path+'pp_closed.csv',header=4)
        pp_open_const_ae = pd.read_csv(path+'pp_open_const_ae.csv',header=4)
        pp_open = pd.read_csv(path+'pp_open.csv',header=4)

        maxmin = lambda x: x['AttenuationGroundwater (1)'].max()/x['AttenuationGroundwater (1)'].min()
        print(
            maxmin(pp_closed_const_ae),
            maxmin(pp_closed),
            maxmin(pp_open_const_ae),
            maxmin(pp_open),
        )
        fig, ((ax1, ax2),(ax3,ax4)) = plt.subplots(2,2, dpi=300)

        x_smooth = np.linspace(0,23,100)
        y_smooth = CubicSpline(p_diurnal['Time'], p_diurnal['IndoorOutdoorPressure'])(x_smooth)
        ax1.plot(x_smooth, y_smooth)



        x_smooth = np.linspace(0,23,200)
        y_smooth = CubicSpline(ae_diurnal['Time'], ae_diurnal['AirExchangeRate'])(x_smooth)
        ax2.plot(x_smooth, y_smooth, label='Diurnal Ae')


        ax2.plot([0,23],[0.5,0.5], label='Constant Ae')

        pp_open_const_ae.plot(
            x='% Time (h)',
            y='AttenuationGroundwater (1)',
            ax=ax3,
            logy=True,
            label='Max change = %1.2f' % maxmin(pp_open_const_ae),
        )

        pp_open.plot(
            x='% Time (h)',
            y='AttenuationGroundwater (1)',
            ax=ax3,
            logy=True,
            label='Max change = %1.2f' % maxmin(pp_open),
        )


        x_smooth = np.linspace(0,23.6,100)
        y_smooth = CubicSpline(pp_closed['% Time (h)'], pp_closed['AttenuationGroundwater (1)'])(x_smooth)
        ax4.semilogy(x_smooth, y_smooth, label='Max change = %1.2f' % maxmin(pp_closed))

        ax4.semilogy(pp_closed_const_ae['% Time (h)'], pp_closed_const_ae['AttenuationGroundwater (1)'], label='Max change = %1.2f' % maxmin(pp_closed_const_ae))


        ax2.legend(loc='best')
        ax4.legend(loc='best')

        ylims = [5e-6, 1e-4]

        ax1.set(
            ylabel='$p_\\mathrm{in/out} \\; \\mathrm{(Pa)}$',
            title='Simulation input:\nMedian diurnal $p_\\mathrm{in/out}$',
        )

        ax2.set(
            ylabel='$A_e \\; \\mathrm{(1/hour)}$',
            title='Simulation input:\nMedian diurnal $A_e$',
        )

        ax3.set(
            ylim=ylims,
            ylabel='$\\alpha_\\mathrm{gw}$',
            xlabel='Time (hour)',
            title='Simulation result:\nPP open cases'
        )
        ax4.set(
            ylim=ylims,
            xlabel='Time (hour)',
            title='Simulation result:\nPP closed cases'
        )

        plt.tight_layout()

        #plt.savefig('./figures/simulation_predictions/diurnal.png')
        #plt.savefig('./figures/simulation_predictions/diurnal.pdf')

        return


#Diurnal()
#PressureKDE(y_data_log=True,norm_conc=True)
#AttenuationSubslab()
Modeling()
#IndianapolisTime()
#AirExchangeRateKDE()
plt.show()
