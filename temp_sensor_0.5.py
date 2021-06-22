#!/usr/bin/env python3


#  Temperature Sensor Main Program  #
#  By Jonathan Crossley
#  Version:
#    - 0.5 - 9 June 2021
#      - Created title block, version numbering
#      - Cleaned up comments

from temp_support import *


#--- make directory/folder (even if one is not there) for datalogs with the start date on the folder

print("-------------STARTING-------------")   #Not for final product, remove after testing
start_time = time.time()

temp_rate = 0   #possibly move to initial config file???
run_i = 0    #possibly move to initial config file???
out_p_i = 0   #possibly move to initial config file???
dl_i = 0    #possibly move to initial config file???
dl_start_time = time.strftime(DL_START_STR)

fill_in_hysteresis()
print(DRINKS_TABLE)   #Not for final product, remove after testing
drink_r = 0
drink_t = ''

while True:
    loop_time = time.time()
    error_num = 0

    start_read_time = time.time()    # are these needed anymore after testing???
    humd, temp = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN, SENSOR_READ_RETRIES)

    sensor_return, temp, humd, error_num = sensor_range_check(temp, humd)
    if not sensor_return:
        dl_arr[dl_i] = (time.time()-start_time, time.time(), int(time.strftime(DL_LOCAL_TIME_STR)),
                        0, 0, 0, 0, 0, error_num)
        dl_i += 1
        read_error_count += 1    # are these needed anymore after testing???
        #######################################################################################################
        continue   #???This might be bad to have, better to print out what happen and record max values???

    read_time = time.time() - start_read_time    # are these needed anymore after testing???

    if read_time > max_read_time:    # are these needed anymore after testing???
        max_read_time = read_time    # are these needed anymore after testing???

    if not run_arr_full:
        run_arr[run_i] = temp
        run_i += 1

        if run_i == RUN_AVG_LENG:
            run_arr_full = True
            fill_run_arr(run_arr)
            drink_r, drink_t = set_initial_drink_row(np.mean(run_arr))
    else:
        outlier_return, temp_rate = outlier_check(run_arr, temp, temp_rate)
        if not outlier_return:
            run_arr[run_i%RUN_AVG_LENG] = temp
            run_i += 1
            out_p_i = outlier_persist_reset(outlier_persist_arr)
            drink_r, drink_t = drink_check(np.mean(run_arr), drink_r)

        else:
            print(ERROR_3)   # are these needed anymore after testing???
            error_num = 3
            outlier_count += 1   # are these needed anymore after testing???

            if temp_rate < TEMP_RATE_LIMIT:
                outlier_persist_arr[out_p_i] = temp
                out_p_i +=1

                if out_p_i == RUN_AVG_LENG:
                    error_num = reset_running_array(run_arr, outlier_persist_arr)
                    drink_r, drink_t = drink_check(np.mean(run_arr), drink_r)
                    out_p_i = outlier_persist_reset(outlier_persist_arr)


    dl_arr[dl_i] = (time.time()-start_time, time.time(), int(time.strftime(DL_LOCAL_TIME_STR)),
                        temp, np.mean(run_arr), temp_rate, humd, drink_r, error_num)
    dl_i += 1

    if dl_i == DL_LENG:
        data_log_save(dl_start_time, dl_arr)
        dl_i = 0
        for i in range(0,DL_LENG):
            dl_arr[i] = (0, 0, 0, 0, 0, 0, 0, 0, 0)   # Is this more or less efficient than creating new array???
        dl_start_time = time.strftime(DL_START_STR)


    ######   FOR DEBUGGING & TESTING   #######################
    ###########################################################################################
    # Not sure if this should be in final product and/or in data logged for history purposes
    # Possibly have a 2nd log file for just max/min of that period AND all time max/min,
    #    and possibly other data like total_time, max_read_time, error counts, outlier counts, etc. 
    if run_i == 1:
        max_temp = temp
        min_temp = temp
        max_humd = humd
        min_humd = humd
        #max_sigma = 0
        max_temp_rate = 0
        max_temp_time = time.strftime(DATE_STR) 
        min_temp_time = time.strftime(DATE_STR)
        max_humd_time = time.strftime(DATE_STR)
        min_humd_time = time.strftime(DATE_STR)
        #max_sigma_time = time.strftime(DATE_STR)
        max_temp_rate_time = time.strftime(DATE_STR)

    if temp > max_temp:
        max_temp = temp
        max_temp_time = time.strftime(DATE_STR)
    if temp < min_temp:
        min_temp = temp
        min_temp_time = time.strftime(DATE_STR)
    if humd > max_humd:
        max_humd = humd
        max_humd_time = time.strftime(DATE_STR)
    if humd < min_humd:
        min_humd = humd
        min_humd_time = time.strftime(DATE_STR)
    #if abs(outlier_check_return[1]) > abs(max_sigma):
    if abs(temp_rate) > abs(max_temp_rate):
        #max_sigma = outlier_check_return[1]
        max_temp_rate = temp_rate
        #max_sigma_time = time.strftime(DATE_STR)
        max_temp_rate_time = time.strftime(DATE_STR)


    ################# Not for final product
    #print(f'{temp/DECIMAL_PRECISION:.1f}\u00B0 C')   #degrees symbol
    print(f'{temp/DECIMAL_PRECISION:.1f} C')
    print(f'{humd} %')
    print(f'Drink:  {drink_t}')
    print(f'Drink row:  {drink_r}')

    # Print out the running average and data log array to watch creation and filling and resetting and writing to file
    print(f'Running Average Array:\n{run_arr}')  # Running average
    #print(f'Data Log Array:\n{dl_arr}')  # Data log

    #print(f'Max Sigma:  {max_sigma:.3f} \u03C3')   #sigma symbol
    #print(f'Max Sigma:  {max_sigma:.3f} sigma')
    print(f'Max Temp Rate:  {max_temp_rate:.3f} deg/min')
    #print(f'    @:  {max_sigma_time}')
    print(f'    @:  {max_temp_rate_time}')

    #print(f'Max Temp:  {max_temp/DECIMAL_PRECISION:.1f}\u00B0 C')   #degrees symbol
    print(f'Max Temp:  {max_temp/DECIMAL_PRECISION:.1f} C')
    print(f'    @:  {max_temp_time}')
    #print(f'Min Temp:  {min_temp/DECIMAL_PRECISION:.1f}\u00B0 C')   #degrees symbol
    print(f'Min Temp:  {min_temp/DECIMAL_PRECISION:.1f} C')
    print(f'    @:  {min_temp_time}')
    print(f'Max Humidity:  {max_humd} %')
    print(f'    @:  {max_humd_time}')
    print(f'Min Humidity:  {min_humd} %')
    print(f'    @:  {min_humd_time}')

    print(f'Read Error Count:    {read_error_count}')
    print(f'Outlier Count:  {outlier_count}')
    print(f'Read Time:    {read_time:.3f} sec')
    print(f'Max Read Time:  {max_read_time:.3f} sec')
    print_time_duration(time.time() - start_time)
    print("-------------END-------------")
    ###########################################################################################


    #Also need way to quit program while testing
    #Also be able to save datalog when power is removed or power button is pushed or something
    while (time.time() - loop_time) < SECS_BETWEEN_READS: 
        time.sleep(0.5)
