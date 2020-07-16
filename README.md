# Cognitests
Cognitests is a tool for creating, running and analyzing cognitive neuropsychology tests.
![Welcome-Cognitests](https://user-images.githubusercontent.com/24806155/57361118-696ec680-7184-11e9-85ac-7c56d06defab.png)

## Table of Contents  
- [Cognitests](#cognitests)
  * [Requirements](#Requirements)
  * [Installation](#Installation)
  * [Packeging](#Packeging)
  * [Docs](#docs)
  
## Requirements
  EMOTIV headset (Epoc+/Insight)<br />
  Python 3.X, tested with 3.7<br />
  Cortex Service V1.X, Cortex V2.X is not supported yet. <br />
  InfluxDB V1.7<br />
  
## Installation
1.	Clone or download Cognitests from our GitHub: https://github.com/shohamj/Cognitests
2.	Download and install the latest version of Python from the official site: https://www.python.org/downloads/
3.	From the location where you saved Cognitests, run “pip install -r requirements.txt”.
4.	Install Cortex V1 using the provided installer file. Please note this part requires admin privileges.
5.	Download InfluxDB from https://portal.influxdata.com/downloads/
6.	Locate the folder “influxdb” where you saved Cognitests and extract the InfluxDB files into in, make sure to use the “influxdb.conf” file provided with Cognitests (file is located under the influxdb folder) instead of the one downloaded from InfluxDB.
7.	Run Cognitests with the command “python run.py”

## Packeging
After installing Cognitests successfuly, run "python pyinstaller/pyinstaller.py".
When the process is over, the executable folder will show up.

