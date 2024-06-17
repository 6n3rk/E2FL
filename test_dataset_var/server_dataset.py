from power import Monitor
import Monsoon.sampleEngine as sampleEngine
from log import WrlsEnv
from datetime import datetime
import subprocess, os, logging, time, socket, pickle
import paramiko, yaml
import re
import argparse
from typing import List, Tuple

import argparsefrom typing import List, Tuple
import flwr as fl
from flwr.common import Metrics

import torch
import torchvision.transforms as transforms
from torchvision.datasets import MNIST
from torch.utils.data import DataLoader
import torch.nn as nn
import torch.optim as optim


parser = argparse.ArgumentParser(description="Flower Embedded devices")
parser.add_argument(
    "--server_address",
    type=str,
    default="0.0.0.0:8080",
    help=f"gRPC server address (deafault '0.0.0.0:8080')",
)
parser.add_argument(
    "--rounds",
    type=int,
    default=5,
    help="Number of rounds of federated learning (default: 5)",
)
parser.add_argument(
    "--sample_fraction",
    type=float,
    default=1.0,
    help="Fraction of available clients used for fit/evaluate (default: 1.0)",
)
parser.add_argument(
    "--min_num_clients",
    type=int,
    default=2,
    help="Minimum number of available clients required for sampling (default: 2)",
)
_UPTIME_RPI3B = 500

# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
# logging.debug, logging.info, logging.warning, logging.error, logging.critical
class CustomFormatter(logging.Formatter):
    
    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = "%(asctime)s - %(levelname)s - %(message)s"

    FORMATS = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: grey + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

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
    return result

def change_WiFi_interface_client(client_ssh, interf = 'wlan0', channel = 11, rate = '11M', txpower = 15):
    # change Wi-Fi interface 
    stdin, stdout, stderr = client_ssh.send(f"iwconfig {interf} channel {channel} rate {rate} txpower {txpower}") # exec_command
    time.sleep(2)
    
    # Receive the output
    output = client_ssh.recv(65535).decode() # 65535 is the maximum bytes that can read by recv() method.

    if 'error' in output.lower() or 'command not found' in output.lower():
            logger.error("Error detected in the command output.")
            return False
    else:
        logger.info("iwconfig executed successfully.")
        logger.info(output)
    
    return True

def kill_running_iperf3_server():
    result = subprocess.run(['ps', 'aux'], stdout=subprocess.PIPE, text=True)
    process_list = result.stdout.splitlines()

    # Look for iperf3 server process
    for process in process_list:
        if 'iperf3 -s' in process:
            # Extract process ID
            parts = process.split()
            pid = parts[1]
            
            # Kill the iperf3 server process
            try:
                subprocess.run(['kill', '-9', pid], check=True)
                logger.info(f"iperf3 server process (PID: {pid}) has been terminated.")
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to terminate iperf3 server process (PID: {pid}): {e}")
                exit(1)

def start_iperf3_server(server_ip, port=5201):
    """Start a iperf3 server at a server A asynchronously."""
    kill_running_iperf3_server()
    logger.info(f"Kill existing iperf3 server process and wait.")
    time.sleep(10)
    # Start iperf3 server. (Waitting at 5201 port)
    return subprocess.run(['iperf3', '-s', '--bind', str(server_ip), '-p', str(port)],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    #subprocess.Popen(['iperf3', '-s', '--bind', str(server_ip), '-p', str(port)], 
    #                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def run_iperf3_client(client_SSH, server_ip, duration = 10, server_port = 5201):
    """Run a iperf3 client at a edge device B to send data to server A."""
    try:
        # Run iperf3 client command.
        command = 'iperf3 -c '+str(server_ip)+' -p '+str(server_port)+' -t '+str(duration)
        output = client_SSH.send(command) # exec_command
        time.sleep(2)
    
        # Receive the output
        output = client_SSH.recv(65535).decode() # 65535 is the maximum bytes that can read by recv() method.
        
        if 'error' in output.lower() or 'command not found' in output.lower():
            logger.error("Error detected in the command output.")
            return False
        else:
            logger.info("iperf3 executed successfully.")
            logger.info("===============(Terminal Output START)===============")
            logger.info(output)
            logger.info("===============(Terminal Output  END )===============")

        '''
        # Print the results.
        for line in stdout.read().splitlines():
            logger.info('client_SSH:')
            logger.info(line.decode('utf-8'))
        for line in stderr.read().splitlines():
            logger.error(line.decode('utf-8'))
            return False
        '''
    except:
        logger.error("run_iperf3_client failed.")
        return False
    return True

def get_client_SSH(client_ip, wait_time):
    # Wait for boot up
    print(f"Wait {wait_time} seconds for the edge device to boot.")

    # Set up SSH service
    client_SSH = paramiko.SSHClient()
    client_SSH.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # Add the host key automatically AutoAddPolicy()
    mykey = paramiko.RSAKey.from_private_key_file(private_key_path)

    # ssh -i {rsa} {USER}@{IP_ADDRESS}
    try_count = 0
    start_time = time.time()
    while 1:
        print(f'{try_count} try ...')
        try:
            client_SSH.connect(hostname = client_ip, port = ssh_port, username = client_ssh_id, passphrase="", pkey=mykey, look_for_keys=False)
            break
        except:
            try_count = try_count + 1
            pass
        time.sleep(10)
        if time.time() - start_time > _UPTIME_RPI3B:
            try:
                client_SSH.connect(hostname = client_ip, port = ssh_port, username = client_ssh_id, passphrase="", pkey=mykey, look_for_keys=False)
            except Exception as e:
                logger.error("SSH is failed: ", e)
                logger.error(private_key_path)
                exit(1)

    if client_SSH.get_transport() is not None and client_SSH.get_transport().is_active():
        logger.info('An SSH connection for the client is established.')
        # Enable Keep Alive
        client_SSH.get_transport().set_keepalive(30)
        logger.debug("Set the client_SSH's keepalive option.")
    else:
        logger.debug("client_SSH is closed. exit()")
        exit()

    client_shell = client_SSH.invoke_shell()

    return client_shell


# FL; define metric aggregation function
def weighted_average(metrics: List[Tuple[int, Metrics]]):
    """This function averages teh `accuracy` metric sent by the clients in a `evaluate`
    stage (i.e. clients received the global model and evaluate it on their local
    validation sets)."""
    # Multiply accuracy of each client by number of examples used
    accuracies = [num_examples * m["accuracy"] for num_examples, m in metrics]
    examples = [num_examples for num_examples, _ in metrics]

    # Aggregate and return custom metric (weighted average)
    return {"accuracy": sum(accuracies) / sum(examples)}


def fit_config(server_round: int):
    """Return a configuration with static batch size and (local) epochs."""
    config = {
        "epochs": 3,  # Number of local epochs done by clients
        "batch_size": 16,  # Batch size to use by clients during fit()
    }
    return config


def fl_server(server_address, num_clients=4, sample_frac=1.0, round=3):
    # Define strategy
    strategy = fl.server.strategy.FedAvg(
        fraction_fit=sample_frac,
        fraction_evaluate=sample_frac,
        min_fit_clients=num_clients,
        on_fit_config_fn=fit_config,
        evaluate_metrics_aggregation_fn=weighted_average,
    )
    # Start Flower server
    fl.server.start_server(
        server_address=server_address,
        config=fl.server.ServerConfig(num_rounds=round),
        strategy=strategy,
    )

# default parameters
root_path = os.path.abspath(os.getcwd())+'/'
node_A_name = 'rpi3B+'
node_A_mode = "PyMonsoon"
client_ssh_id = 'pi'
ssh_port = 22
iperf3_server_port = 5203
iperf3_duration = 10

# FL parameters
FL_num_clients = 4
FL_sample_frac = 1.0
FL_round = 3

# Set up logger
logger = logging.getLogger("test")
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(CustomFormatter())
logger.addHandler(ch)

# Set up Power Monitor
node_A_vout = 5.0
node_A_triggerBool = True
node_A_numSamples = sampleEngine.triggers.SAMPLECOUNT_INFINITE
node_A_thld_high = 100
node_A_thld_low = 10
node_A_CSVbool = False #True
node_A_CSVname = "default"
rpi3B = Monitor.PowerMon(   node = node_A_name,
                            vout = node_A_vout,
                            mode = node_A_mode,
                            ConsoleIO = False)
rpi3B.setTrigger(   bool = node_A_triggerBool,
                    thld_high = node_A_thld_high,
                    thld_low = node_A_thld_low )
rpi3B.setCSVOutput( bool = node_A_CSVbool,
                    filename = node_A_CSVname)

# Read the YAML config file.
with open(root_path+'config.yaml', 'r') as file:
    config = yaml.safe_load(file)  # Read YAML from the file and convert the structure of the python's dictionary.

# Get IP addresses.
server_ip = config['server']['host']  # Extract 'host' key's value from the 'server' key
client_ip1 = config['RPi3B+']['host']
client_ip2 = config['RPi3B+_b']['host']
client_ip3 = config['RPi4B']['host']
client_ip4 = config['RPi5']['host']
private_key_path = root_path + config['RPi3B+']['ssh_key']
client_interf = config['RPi3B+']['interface']

if server_ip or client_ip1:
    print(f"The IP address of the server is: {server_ip}")
    print(f"The IP address of the client is: {client_ip1}, {client_ip2}, {client_ip3}, {client_ip4}")
    print(f"The ID of the client is: {client_ssh_id}")
else:
    print("IP address could not be determined")
    exit(1)


# set client_SSH
client_shells = []
for c_ip in [client_ip1, client_ip2, client_ip3, client_ip4]:
    client_shells.append(get_client_SSH(client_ip = c_ip, wait_time = _UPTIME_RPI3B))

# Start the FL server.
try:
    fl_server(server_address=server_ip, \
              num_clients=FL_num_clients, sample_frac=FL_sample_frac, round=FL_round)
    logger.info("Start FL server.")
    # Wait for server to start fl properly.
    time.sleep(5)
except Exception as e:
    logger.error('FL is failed: ', e)
    exit(1)

# Prepare a bucket to store the results.
measurements_dict = []

WiFi_rates = [1] #[1, 2, 5.5, 11, 6, 9, 12, 18, 24, 36, 48, 54]

for rate in WiFi_rates:
    time_records = []

    # Log the start time.
    time_records.append(time.time())

    # Start power monitoring.
    rpi3B.startSampling(numSamples = node_A_numSamples) # it will take measurements every 200us
    logger.info('Start power monitor.')

    # run fl client to client_shells
    for cid in range(0,5):
        client_cmd = "python3.10 ./client_dataset.py --cid={cid} --server_address={server_ip} --mnist"
        output = client_shells[cid].send(client_cmd)
        time.sleep(2)
    

    output = client_shells[0].recv_exit_status() #recv(65535).decode()
    if 'error' in output.lower() or 'command not found' in output.lower():
        logger.error("Error detected in the command output.")
        exit(1)
    else:
        logger.info("client_dataset.py executed successfully.")
        logger.info("===============(Terminal Output START)===============")
        logger.info(output)
        logger.info("===============(Terminal Output  END )===============")

    # End power monitoring.
    rpi3B.stopSampling()
    samples = rpi3B.getSamples()

    # Log the end time.
    time_records.append(time.time())
    logger.info([f'Wi-Fi end(rate: {rate})',time.time()])

    measurements_dict.append({'rate': rate, 'time': time_records, 'power': samples})

# Close the SSH connection.
for client_SSH in client_shells:
    client_SSH.close()

# Terminate the iperf3 server process.
# server_process.terminate()
# logger.info("Close the iperf3 serveer.")

# Save the data.
current_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
filename = f"data_{current_time}.pickle"
with open(filename, 'wb') as handle:
    pickle.dump(measurements_dict, handle, protocol=pickle.HIGHEST_PROTOCOL)
logger.info(f"The measurement data is saved as {filename}.")





# Load data
transform = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize((0.1307,), (0.3081,))
])

trainset = MNIST('./data', train=True, download=True, transform=transform)
trainloader = DataLoader(trainset, batch_size=32, shuffle=True)
testset = MNIST('./data', train=False, download=True, transform=transform)
testloader = DataLoader(testset, batch_size=32, shuffle=False)




