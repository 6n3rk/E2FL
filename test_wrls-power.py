from power import Monitor
import Monsoon.sampleEngine as sampleEngine
from log import WrlsEnv
import subprocess
import re
import iperf3
import logging
import time
from datetime import datetime
import socket
import paramiko

logging.basicCOnfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
# logging.debug, logging.info, logging.warning, logging.error, logging.critical

'''
Client-Server Architecture
- Client: Raspberry Pi (conneceted to power monitor as power supplier)
- Server: Linux Desktop (conneceted to power monitor's USB interface)

Wi-Fi interface table
'Wi-Fi AP': IPTIME AX2002-Mesh
- b, g, n, ax 20MHz, Korea
- TX power = 100
- Beacon 100ms


'AX201'
'bcm434355c0' on the RPI3+/RPI4 https://github.com/seemoo-lab/nexmon
-> ~ 802.11a/g/n/ac with up 80 MHz
data rate
- 802.11b: [1, 2, 5.5, 11] # Mbps
- 802.11g: [6, 9, 12, 18, 24, 36, 48, 54] # Mbps
- 802.11n: [
        6.5, 7.2, 13.5, 15,  
        13, 14.4, 27, 30, 19.5, 21.7, 40.5, 45,
        26, 28.9, 54, 60, 39, 43.3, 81, 90,
        52, 57.8, 108, 120, 58.5, 65, 121.5, 135, 65, 72.2, 135, 150,
        13, 14.4, 27, 30, 
        26, 28.9, 54, 60, 39, 43.3, 81, 90,
        52, 57.8, 108, 120, 78, 86.7, 162, 180,
        104, 115.6, 216, 240, 117, 130, 243, 270, 130, 144.4, 270, 300,
        19.5, 21.7, 40.5, 45,
        39, 43.3, 81, 90, 58.5, 65, 121.5, 135, 
        78, 86.7, 162, 180, 117, 130, 243, 270,
        156, 173.3, 324, 360, 175.5, 195, 364.5, 405, 195, 216.7, 405, 450,
        26, 28.8, 54, 60,
        52, 57.6, 108, 120, 78, 86.8, 162, 180,
        104, 115.6, 216, 240, 156, 173.2, 324, 360,
        208, 231.2, 432, 480, 234, 260, 486, 540, 260, 288.8, 540, 600
]

iw https://wireless.wiki.kernel.org/en/users/documentation/iw
'''

def get_ip_address():
    try:
        hostname = socket.gethostname()
        ip_addr = socket.gethostbyname(hostname)
        return ip_addr
    except socket.error as e:
        print(f'Unable to get IP address: {e}')
        return None

def change_WiFi_interface(interf = 'wlan0', channel = 11, rate = '11M', txpower = 15):
    # change Wi-Fi interface 
    result = subprocess.run([f"iwconfig {interf} channel {channel} rate {rate} txpower {txpower}"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)

# Set up Power Monitor
node_A_name = 'rpi3B+'
node_A_vout = 5.0
node_A_mode = "PyMonsoon"
node_A_triggerBool = True
node_A_numSamples = 5000
node_A_thld_high = 100
node_A_thld_low = 10
node_A_CSVbool = False#True
node_A_CSVname = "default"
rpi3B = Monitor.PowerMon(   node = node_A_name,
                            vout = node_A_vout,
                            mode = node_A_mode)
'''
    rpi3B.setTrigger(   bool = node_A_triggerBool,
                        numSamples = node_A_numSamples,
                        thld_high = node_A_thld_high,
                        thld_low = node_A_thld_low )
'''
rpi3B.setCSVOutput( bool = node_A_CSVbool,
                    filename = node_A_CSVname)

# Read the client IP address from the yaml file
client_ip = '192.168.0.18'
client_id = 'pi'
client_pwd = 'raspberry'
ssh_port = 22

# Get IP address
server_ip = '192.168.0.17' #get_ip_address()
if server_ip:
    print("The IP address of the server is: ",server_ip)
else:
    print("IP address could not be determined")
    exit(1)

# Set up SSH service



# Set up iperf3
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
iperf_time_interv = 2

iperf_client = iperf3.Client()
iperf_client.server.hostname = '192.168.0.1'
iperf_client.port = 5201
iperf_client.duration = 60
iperf_client.bind_address = '192.168.0.1' # wi-fi interface's ip address


time_records = []


# Set up WiFi interface
# 1. Identify the capabilities of the Wi-Fi interface of the currently running system.
WiFi_rates = [1, 2, 5.5, 11, 6, 9, 12, 18, 24, 36, 48, 54]

# 2. Set the rate (protocl version) of the Wi-Fi interface from the low data rate.
for rate in WiFi_rates:
    # Log the start time.
    time_records.append([f'Wi-Fi start(rate: {rate})',time.time()])

    # Start power monitoring.

    
    rpi3B.startSampling()
    samples = rpi3B.getSamples()


    # Use iperf3 to measure the Wi-Fi interface's power consumption.
    iperf_result = iperf_client.run()

    if iperf_result.error:
        logging.error(iperf_result.error)
    else:
        print("iperf3 is done.")

    # End power monitoring.


    # Log the end time.
    time_records.append(['Wi-Fi end(rate: , )',time.time()])


# Calculate each rate's average power consumption.
current_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
filename = f"data_{current_time}.txt"
try:
    # 파일을 열려고 시도합니다.
    f = open(filename, 'w')
    f.write(time_records)
    f.close()
except OSError as e:
    # OSError 발생 시 오류 코드와 메시지를 출력합니다.
    print(f"Error opening {filename}: {os.strerror(e.errno)}")


# Plot the result.