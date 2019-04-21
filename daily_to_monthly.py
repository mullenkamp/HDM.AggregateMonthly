# -*- coding: utf-8 -*-
"""
Created on Wed Apr  4 09:52:48 2018

@author: michaelek
"""
import pandas as pd
import numpy as np
from pdsql import mssql
from datetime import datetime
import parameters as param

run_time_start = datetime.today().strftime('%Y-%m-%d %H:%M:%S')

#####################################
### Read the hydro log for the last extraction date

ext_system = 'Hydro'

max_date_stmt = "select max(RunTimeStart) from {log_tab} where HydroTable='{ts_tab}' and RunResult='pass' and ExtSystem='{ext_system}'".format(log_tab=param.log_table, ts_tab=param.ts_month_table, ext_system=ext_system)

last_date1 = mssql.rd_sql(server=param.hydro_server, database=param.hydro_database, stmt=max_date_stmt).loc[0][0]

if last_date1 is None:
    last_date = '1900-01-01'
    print('First run')
else:
    last_date = str(last_date1)
    print('Last sucessful date is ' + last_date)
# last_date = '1900-01-01'

try:

    #####################################
    ### Determine which datasets have changed since last run

    print('Process data')

    ## Determine the Dataset type ids to use
    mtypes1 = mssql.rd_sql(param.hydro_server, param.hydro_database, param.mtype_table, ['MTypeID', 'LoggingMethodID'])

    datasets1 = mssql.rd_sql(param.hydro_server, param.hydro_database, param.dataset_type_table, ['DatasetTypeID', 'MTypeID', 'DataCodeID'], where_in={'CTypeID': [param.ctype_id]})

    dtypes1 = pd.merge(datasets1, mtypes1, on='MTypeID')

    stmt1 = param.sql_min_max_stmt.format(tab=param.ts_day_table, mod_date=last_date, dtypes=', '.join(datasets1.DatasetTypeID.astype(str)))

    summ1 = mssql.rd_sql(param.hydro_server, param.hydro_database, stmt=stmt1)
    summ1.FromDate = pd.to_datetime(summ1.FromDate)
    summ1.ToDate = pd.to_datetime(summ1.ToDate)

    ## Filter datasets
    summ1['days'] = (summ1.ToDate - summ1.FromDate).dt.days
    summ2 = summ1[(summ1['days'] >= 20) & (summ1['Count'] >= 20)].copy()

#    sites1 = summ2.ExtSiteID.unique().astype(str)
#    dtypes1 = summ2.DatasetTypeID.unique().astype(str)
#    n_chunks = np.ceil(len(sites1) / float(param.sites_chunk))
#    sites2 = np.array_split(sites1, n_chunks)

    ## Adjust the from and to dates
    mb = pd.offsets.MonthBegin()
    me = pd.offsets.MonthEnd()

    summ2.FromDate = (summ2.FromDate - pd.DateOffset(months=1)).apply(mb)
    summ2.ToDate = (summ2.ToDate - pd.DateOffset(months=1)).apply(me)

    summ3 = pd.merge(summ2, dtypes1, on='DatasetTypeID')

    ### Chunk through the data
    n_data_added = 0

    for index, row in summ3.iterrows():
        print(row.ExtSiteID, row.DatasetTypeID)
        data1 = mssql.rd_sql(param.hydro_server, param.hydro_database, param.ts_day_table, ['DateTime', 'Value', 'QualityCode'], where_in={'ExtSiteID': [row.ExtSiteID], 'DatasetTypeID': [row.DatasetTypeID]}, from_date=str(row.FromDate), to_date=str(row.ToDate), date_col='DateTime')
        if data1.empty:
            continue

        data1.DateTime = pd.to_datetime(data1.DateTime)
        data1.set_index('DateTime', inplace=True)

        grp1 = data1.resample('M')
        count1 = grp1[['Value']].count()
        agg1 = grp1.Value.mean()
        q_code = grp1.QualityCode.min()

        if row.LoggingMethodID == param.logging_method_sum_id:
            count1['days'] = count1.index.daysinmonth
            agg1 = agg1 * count1['days']
            agg1.name = 'Value'

        data2 = pd.concat([agg1, q_code], axis=1)
        data2 = data2[count1.Value >= param.min_data_days].reset_index().copy()
        if data2.empty:
            continue

        data2['ExtSiteID'] = row.ExtSiteID
        data2['DatasetTypeID'] = row.DatasetTypeID
        data2['ModDate'] = run_time_start

        mssql.update_table_rows(data2, param.hydro_server, param.hydro_database, param.ts_month_table, on=['ExtSiteID', 'DatasetTypeID', 'DateTime'])

        n_data_added = n_data_added + len(data2)
        print(n_data_added)

    ### Log sucess!
    run_time_end = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
    log1 = pd.DataFrame([[run_time_start, run_time_end, '1900-01-01', param.ts_month_table, ext_system, 'pass', str(n_data_added) + ' rows were added/updated.']], columns=['RunTimeStart', 'RunTimeEnd', 'DataFromTime', 'HydroTable', 'ExtSystem', 'RunResult', 'Comment'])
    mssql.to_mssql(log1, param.hydro_server, param.hydro_database, param.log_table)

    print('Sucess!')


except Exception as err:
    err1 = err
    print(err1)
    run_time_end = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
    log1 = pd.DataFrame([[run_time_start, run_time_end, '1900-01-01', param.ts_month_table, ext_system, 'fail', str(err1)[:299]]], columns=['RunTimeStart', 'RunTimeEnd', 'DataFromTime', 'HydroTable', 'ExtSystem', 'RunResult', 'Comment'])
    mssql.to_mssql(log1, param.hydro_server, param.hydro_database, param.log_table)



