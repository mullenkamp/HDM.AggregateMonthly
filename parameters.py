# -*- coding: utf-8 -*-
"""
Created on Tue Apr 24 09:29:52 2018

@author: michaelek
"""
import os
from configparser import ConfigParser


#####################################
### Parameters

## Generic
base_dir = os.path.realpath(os.path.dirname(__file__))

ini1 = ConfigParser()
ini1.read([os.path.join(base_dir, os.path.splitext(__file__)[0] + '.ini')])

hydro_server = str(ini1.get('HydroDB', 'server'))
hydro_database = str(ini1.get('HydroDB', 'database'))

log_table = 'HydroLog'

ts_day_table = 'TSDataNumericDaily'
ts_day_summ_table = 'TSDataNumericDailySumm'
ts_month_table = 'TSDataNumericMonthly'

mtype_table = 'MeasurementType'
logging_method_sum_id = 2

dataset_type_table = 'DatasetType'

ctype_id = 1

sites_chunk = 100

min_data_days = 25


sql_min_max_stmt = "select ExtSiteID, DatasetTypeID, min([DateTime]) as FromDate, max([DateTime]) as ToDate, count([DateTime]) as Count from {tab} where ModDate >= {mod_date} and DatasetTypeID in ({dtypes}) group by ExtSiteID, DatasetTypeID"
