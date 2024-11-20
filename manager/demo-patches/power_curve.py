import sys
import json
import math
from time import time
import numpy as np
import control as ct
from iso15118.shared.messages.iso15118_2.datatypes import ProfileEntryDetails
from iso15118.shared.messages.datatypes import PVPMax
from iso15118.shared.messages.enums import UnitSymbol

"""beginning_of_profile_schedule: int= -1
Created on Fri Aug  9 00:37:56 2024
LQRchargeCurve

@author: ANAND
"""
# KS is btwn 1 and 20
def LQRChargeCurve(DepTime, EAmount, PMax, KS):
    # system matrices
    A=np.array([[0]])
    B=np.array([[1]])
    C=np.array([[1]])
    D=np.array([[0]])
     
    #define the initial condition
    x0=np.array([[0]])
   
    # define the time vector for simulation
    startTime=0
    endTime = round(DepTime/60)*60
    numberSamples = round(endTime/60)
    timeVector=np.linspace(startTime,endTime,numberSamples)
   
    # state weighting matrix
    Q=KS/1000
     
    # input weighting matrix
    R=KS*1000

    # system matrices

    sysStateSpace=ct.ss(A,B,C,D)
    xd=np.array([[EAmount]])

    K, S, E = ct.lqr(sysStateSpace, Q, R)

    Acl=A-np.matmul(B,K)
    Bcl=-Acl
     
    # define the state-space model
    sysStateSpaceCl=ct.ss(Acl,Bcl,C,D)
     
    # define the input for closed-loop simulation
    inputCL=np.zeros(shape=(1,numberSamples))
    inputCL[0,:]=xd*np.ones(numberSamples)
    print(f"Created input array with {EAmount=} and {numberSamples=}")
    returnSimulationCL = ct.forced_response(sysStateSpaceCl,
                                          timeVector,
                                          inputCL,
                                          x0)
   

    # YC is state of charge of the vehicle (progress to eamount)
    # UC is power
    # TC is the timevector 
    Yc = returnSimulationCL.states[0,:]
    Uc=  np.transpose(-K*(returnSimulationCL.states[0,:]-inputCL))
    Tc = returnSimulationCL.time

    return Yc, Uc, Tc


'''
    formatCurveData takes the output of the LQR ChargeCurve below, and formats
    it into a JSON string that will be accepted by Node-RED's `chart`
    module.

    @author Katie
'''
def formatCurveData(profile_entry_list):
    # Node-RED expects watts & miliseconds
    yc_curve = [{"x": float(ped.start), "y": float(ped.max_power.value)} for ped in profile_entry_list]
    return {
      "series": ["A"],
      "data": [yc_curve],
      "labels": ["r1"]
    }


'''
    generate_new_schedule is used in `evcc/simulator.py`'s `process_sa_schedules_v2` to
    create a profile_entry list from both the existing `secc_schedule` and a schedule
    generated by the above LQR Charging Optimizer 

    @author Katie
'''
def generate_new_schedule(secc_schedule, uc, tc, departure_time, time_elapsed):
    # time_offset = 24 * # max enteries is 24, so refresh every <24 -ish seconds?
    # Define some helper functions...
    # Evenly sample from the `curve_schedule`< up to the end timestamp
    def sample_schedule(schedule):

        sliced_array = [x for x in schedule if (time_elapsed <= x[1])]
        return sliced_array[0:23]

    # Generates a ProfileEntryDetails obj for the final schedule
    def make_entry(val, timestamp, next_ts):
        # First, convert kWh to kW
        time_delta = (float(next_ts) - float(timestamp)) / 3600
        watts = (1000 * val) / time_delta
        # Then, create the ProfileEntryDetails...
        return  ProfileEntryDetails(
            start=int(timestamp),
            max_power=PVPMax(
                multiplier=0,
                value=watts, # Convert miliwattsHours to WattHours
                unit=UnitSymbol.WATT
            ),
            max_phases_in_use = None
        )

    def convert_tuple_schedule(curve_arr):
        final_ts = curve_arr[-1][1]
        schedule_arr = []
        for i in range(0, len(curve_arr) - 2):
            schedule_arr.append(make_entry(curve_arr[i][0], curve_arr[i][1], curve_arr[i+1][1]))
        print('Done')
        if(len(schedule_arr)): 
            schedule_arr.pop(-1)

        return(schedule_arr)


    def check_new_schedule(curve_arr):
        for schedule in secc_schedule:
            for new_s in curve_arr:
                print(f"Is {schedule.max_power.value} < {new_s.max_power.value}?")
                if new_s.max_power.value > schedule.max_power.value:
                    print('Schedule Creation Error: ', new_s.max_power.value)

    curve_schedule = [(x[0],y) for x, y, in zip(uc, tc)] # UC is in kWh, not kW
    # We get 24 from ISO 15118-2, Table 71.  This is the max number of profile enteries.
    # For some reason, EVerest only accepts 23... Investigate later
    curve_schedule = sample_schedule(curve_schedule)

    if(len(curve_schedule) <= 2): # Check to see if we're done...
        print("Done with profile, defaulting to SECC Schedule")
        return secc_schedule

    curve_schedule = convert_tuple_schedule(curve_schedule)
    print("Returning a curve schedule of:", curve_schedule)

    return curve_schedule

def generate_dummy_schedule():
    watt_vals = [3330, 2300, 1300, 500]
    temp = []

    for i in range(len(watt_vals)):
        temp.append(ProfileEntryDetails(
            start=10 * i,
            max_power=PVPMax(
                multiplier=0,
                value=watt_vals[i],
                unit=UnitSymbol.WATT
            ),
            max_phases_in_use = None
            )
        )
    print('Katie:', temp)
    return temp
    
