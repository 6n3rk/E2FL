from power import Monitor
from log import WrlsEnv
import subprocess
import re

'''
Wi-Fi interface table
'Wi-Fi AP': IPTIME AX2002-Mesh
- b, g, n, ax 20MHz, Korea
- TX power = 100
- Beacon 100ms

'AX201'
'br

'''

def change_WiFi_interface(interf = 'wlan0', channel = 11, rate = '11M', txpower = 15):
    # change Wi-Fi interface 
    result = subprocess.run([f"iwconfig {interf} channel {channel} rate {rate} txpower {txpower}"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)

def setup_iperf3():
    result = subprocess.run([f"iperf3"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    
# Set up WiFi interface
# 1. Identify the capabilities of the Wi-Fi interface of the currently running system.


# 2. Set the rate (protocl version) of the Wi-Fi interface from the low data rate.



# Log the start time.


# Start power monitoring.

# Use iperf3 to measure the Wi-Fi interface's power consumption.
'''
iperf3

-s : server mode
-c : client mode
-p {#}: port
-u : use UDP rather than TCP
-b : indicate bandwidth when using UDP
-t {#}: time interval
-w {#}: TCP window size (socket buffer size)
-M {#}: set TCP maximum setment size (MTU - 40 bytes)
-N : set TCP no delay, disabling Nagle's Algorithm
-V : set the domain to IPv6
-d : measure bi-direcitonal
-n {#}: number of bytes to transmit
-F {name}: input the data to be transmitted from a file
-I : input the data to be transmitted from stdin
-P #: number of parallel client thrads to run
-T : time-to-live, for multicast (default 1)
'''
iperf_server = '192.168.0.1'
iperf_time_interv = 2
iperf_port = 123


# End power monitoring.


# Log the end time.


# Calculate each rate's average power consumption.


# Plot the result.