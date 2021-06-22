#!/usr/bin/env python3

#  ------------ Temperature Sensor Support Fuctions & Variables ------------
#  By Jonathan Crossley
#  Version:
#    - 0.5 - 9 June 2021  (Initial Version)
#      - Created title block, version numbering
#      - Cleaned up comments

#     0.6?? - Added functions

import time
import Adafruit_DHT
import numpy as np

# --------- Error Values ---------
ERROR_1 = "Sensor_Error: Sensor returned None"
ERROR_2 = "Sensor_Error: Temperature/humidity value beyond sensor range..."
ERROR_3 = "Outlier_Error: Temperature exceeded outlier bounds..."
ERROR_4 = "Outlier_Persistant_Error: Outlier persisted, reset running array..."

# --------- Sensor Values ---------
# Sensor: AOSONG AM2303 (DHT22)
DHT_SENSOR = Adafruit_DHT.AM2302
DHT_PIN = 4         # GPIO #4

TEMP_MAX = 80       # deg C
TEMP_MIN = -40      # deg C
TEMP_PRECISION = 0.5    # +/- 0.5 deg C

HUMD_MAX = 100      # % relative humidity
HUMD_MIN = 0        # % relative humidity
HUMD_PRECISION = 2      # +/- 2 %

SECS_BETWEEN_READS = 30   #(20-30 for testing) 45-55 for operational??
SENSOR_READ_RETRIES = 25
DECIMAL_PRECISION = 10

# --------- Drink Values ---------
DRINKS_TABLE = [['lower_limit','temp_mid','upper_limit','drink'],  #0
                [-20,-20,-20,'ren 96%'],  #1
                [-11,-11,-11,'ren 40%'],  #2
                [-10,-10,-10,'karsk'],  #3
                [-9,-9,-9,'sterk teknert'],  #4
                [-8,-8,-8,'svak teknert'],  #5
                [-7,-7,-7,'kakao with brandy og chilli'],  #6
                [-6,-6,-6,'kakao with cognak'],  #7
                [-5,-5,-5,'kakao with cognak og krem'],  #8
                [-4,-4,-4,'kakao with krem'],  #9
                [-3,-3,-3,'svart te'],  #10
                [-2,-2,-2,'frukt te'],  #11
                [-1,-1,-1,'ingefaer te'],  #12
                [0,0,0,'is vann/slush'],  #13
                [1,1,1,'strawberry daiquiri'],  #14
                [2,2,2,'sangria'],  #15
                [3,3,3,'sider - breezer'],  #16
                [4,4,4,'champagne'],  #17
                [5,5,5,'musserende vin'],  #18
                [6,6,6,'riesling'],  #19
                [7,7,7,'pino blanc'],  #20
                [8,8,8,'rosevin'],  #21
                [9,9,9,'chablis'],  #22
                [10,10,10,'bayer'],  #23
                [12,12,12,'sot vin'],  #24
                [13,13,13,'jule ol'],  #25
                [14,14,14,'litt rodvin'],  #26
                [15,15,15,'madira'],  #27
                [16,16,16,'torr sterkvin'],  #28
                [18,18,18,'kraftig rodvin'],  #29
                [19,19,19,'drikk ol']]  #30

LOWER_LIM_IND = DRINKS_TABLE[0].index('lower_limit')
TEMP_MID_IND = DRINKS_TABLE[0].index('temp_mid')
UPPER_LIM_IND = DRINKS_TABLE[0].index('upper_limit')
DRINK_LIST_IND = DRINKS_TABLE[0].index('drink')

TABLE_LEN = len(DRINKS_TABLE)
HYSTER_ZONE = 0.1

# --------- Datalog Values ---------
#12 hours = 720 mins, 18 hrs = 1080 mins, 24 hrs = 1440 mins  (15 mins for testing)
MINS_OF_HISTORICAL_DATA = 720
DL_LENG = int(MINS_OF_HISTORICAL_DATA*60 / SECS_BETWEEN_READS)

# Headers for datalog array and csv
#HEADER_KEY = ('total_time','epoch_time','local_time','temp','running_average','temp_rate','humd','drink_text','error_num')   Possible???
HEADER_KEY = ('total_time','epoch_time','local_time','temp','running_average','temp_rate','humd','drink_row','error_num')
HEADER_KEY_STR = ','.join(map(str, HEADER_KEY))
HEADER_TYPE = (np.float, np.float, np.uint16, np.int16, np.int16, np.float, np.uint16, np.uint8, np.uint8)

dl_arr = np.zeros(DL_LENG, dtype={'names':HEADER_KEY,'formats':HEADER_TYPE})

# --------- Running Average & Outlier Values ---------
RUN_AVG_LENG = 9
run_arr = np.zeros(RUN_AVG_LENG, dtype=np.int16)
run_arr_full = False
outlier_persist_arr = np.zeros(RUN_AVG_LENG, dtype=np.int16)

TEMP_RISE_LIMIT = 2.45  # Degrees/Min
TEMP_DROP_LIMIT = -2.2  # Degrees/Min
TEMP_RATE_LIMIT = 3.5  # Degrees/Min

# --------- String Formats ---------
DATE_STR = '%H:%M, %a %d %b %Y'
DL_LOCAL_TIME_STR = '%H%M'
DL_START_STR = '_%d_%b_%Y__%H%M_'
DL_END_STR = '%H%M'

# --------- Debugging Values ---------
read_error_count = 0
outlier_count = 0
max_read_time = 0


#  --------- fill_in_hysteresis Function ---------
#  Take Drinks table and calculate the upper and lower limits to change from
#    one drink to the next, while also adding a hysteresis band to limit
#    "chattering" values
#  Version:
#    - 0.5 - 9 June 2021  (Initial Version)
def fill_in_hysteresis():
    for i in range(1,TABLE_LEN):
        if i == 1:
            DRINKS_TABLE[i][UPPER_LIM_IND] = DRINKS_TABLE[i][TEMP_MID_IND] + \
                (DRINKS_TABLE[i+1][TEMP_MID_IND] - DRINKS_TABLE[i][TEMP_MID_IND]) / 2 + HYSTER_ZONE
        elif i == TABLE_LEN - 1:
            DRINKS_TABLE[i][LOWER_LIM_IND] = DRINKS_TABLE[i][TEMP_MID_IND] - \
                (DRINKS_TABLE[i][TEMP_MID_IND] - DRINKS_TABLE[i-1][TEMP_MID_IND]) / 2 - HYSTER_ZONE
        else:
            DRINKS_TABLE[i][LOWER_LIM_IND] = DRINKS_TABLE[i][TEMP_MID_IND] - \
                (DRINKS_TABLE[i][TEMP_MID_IND] - DRINKS_TABLE[i-1][TEMP_MID_IND]) / 2 - HYSTER_ZONE
            DRINKS_TABLE[i][UPPER_LIM_IND] = DRINKS_TABLE[i][TEMP_MID_IND] + \
                (DRINKS_TABLE[i+1][TEMP_MID_IND] - DRINKS_TABLE[i][TEMP_MID_IND]) / 2 + HYSTER_ZONE

#  --------- set_initial_drink_row Function ---------
#  Set the initial drink row once average temperature is determined
#  Version:
#    - 0.5 - 9 June 2021  (Initial Version)
def set_initial_drink_row(temp):
    for i in range(1,TABLE_LEN):
        if i != TABLE_LEN - 1:
            if i == 1 and temp < DRINKS_TABLE[i][TEMP_MID_IND]:
                return i, DRINKS_TABLE[i][DRINK_LIST_IND]
            elif temp >= DRINKS_TABLE[i][TEMP_MID_IND] and temp < DRINKS_TABLE[i+1][TEMP_MID_IND]:
                return i, DRINKS_TABLE[i][DRINK_LIST_IND]
        else:
            return TABLE_LEN - 1, DRINKS_TABLE[TABLE_LEN - 1][DRINK_LIST_IND]

#  --------- drink_check Function ---------
#  Check which drink row is associated with the current average temperature
#  Version:
#    - 0.5 - 9 June 2021  (Initial Version)
def drink_check(temp, drink_r):
    inbounds = False
    temp = temp / DECIMAL_PRECISION

    while inbounds == False:
        if (drink_r == 1 and temp < DRINKS_TABLE[drink_r][UPPER_LIM_IND]) or \
            (drink_r == (TABLE_LEN - 1) and temp > DRINKS_TABLE[drink_r][UPPER_LIM_IND]):
            return drink_r, DRINKS_TABLE[drink_r][DRINK_LIST_IND]

        if temp > DRINKS_TABLE[drink_r][UPPER_LIM_IND]:
            drink_r += 1
        elif temp < DRINKS_TABLE[drink_r][LOWER_LIM_IND]:
            drink_r -= 1
        else:
            inbounds = True

    return drink_r, DRINKS_TABLE[drink_r][DRINK_LIST_IND]

#  --------- sensor_range_check Function ---------
#  Check temperature and humdity readings from sensor are not empty
#  Version:
#    - 0.5 - 9 June 2021  (Initial Version)
def sensor_range_check(temp, humd):
    if temp is None or humd is None:
        print(ERROR_1)   # are these needed anymore after testing???
        return 0, temp, humd, 1
    else:
        humd = int(humd)
        temp = int(temp * DECIMAL_PRECISION)

    if temp>(TEMP_MAX+TEMP_PRECISION)*DECIMAL_PRECISION or \
        temp<(TEMP_MIN-TEMP_PRECISION)*DECIMAL_PRECISION or \
        humd>(HUMD_MAX+HUMD_PRECISION) or humd<(HUMD_MIN-HUMD_PRECISION):
        print(ERROR_2)   # are these needed anymore after testing???
        return 0, temp, humd, 2
    else:
    	return 1, temp, humd, 0

def print_time_duration(total_time):
    print('Total time:  ', end = '')
    years = total_time//31536000
    months = total_time//2628288
    days = total_time//86400
    hours = total_time//3600
    minutes = total_time//60
    if years > 0:
        print(f'{years:.0f} yrs, ', end = '')
    if months > 0:
        print(f'{months%12:.0f} mons, ', end = '')
    if days > 0:
        print(f'{days%30:.0f} days, ', end = '')
    if hours > 0:
        print(f'{hours%24:.0f} hrs, ', end = '')
    if minutes > 0:
        print(f'{minutes%60:.0f} mins, ', end = '')
    print(f'{total_time%60:.0f} sec')

def fill_run_arr(run_arr):
    med = np.median(run_arr)
    for i in range(0,RUN_AVG_LENG):
        run_arr[i] = med

def outlier_check(run_arr, new_temp, temp_rate):  # Need tuning, not sure this is the best method  
    #std = np.std(run_arr)
    #if std == 0:
    #	std = 0.01

    #sigma = (new_temp - np.mean(run_arr)) / std
    #new_temp_rate = abs(new_temp - np.mean(run_arr)) / ((RUN_AVG_LENG * (SECS_BETWEEN_READS/60)) / 2)
    temp_rate = ((new_temp - np.mean(run_arr)) / ((RUN_AVG_LENG * (SECS_BETWEEN_READS/60)) / 2)) / DECIMAL_PRECISION

    #if new_temp_rate > TEMP_RATE_LIMIT:
    if temp_rate > TEMP_RISE_LIMIT or temp_rate < TEMP_DROP_LIMIT:
        return True, temp_rate
    else:
        return False, temp_rate

    #if sigma >= SIGMA_UPPER_LIMIT or sigma <= SIGMA_LOWER_LIMIT:
    #    return True, sigma
    #else:
    #    return False, sigma

def outlier_persist_reset(outlier_persist_arr):
    for i in range(0,RUN_AVG_LENG):
        outlier_persist_arr[i] = 0
    return 0

def reset_running_array(run_arr, outlier_persist_arr):
    print(ERROR_4)   # are these needed anymore after testing???
    for i in range(0,RUN_AVG_LENG):
        run_arr[i] = outlier_persist_arr[i]
    return 4

def data_log_save(dl_start_time, dl_arr):
    dl_end_time = time.strftime(DL_END_STR)
    np.savetxt("./test_data_logs/log" + dl_start_time + dl_end_time + ".csv", dl_arr, delimiter=",",
        header=HEADER_KEY_STR, comments="")

def data_log_dir_setup(dl_start_time):
    np.savetxt("./test_data_logs/log" + dl_start_time + dl_end_time + ".csv", dl_arr, delimiter=",",
        header=HEADER_KEY_STR, comments="")


