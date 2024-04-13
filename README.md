# System Monitor Bot
This bot provides the ability to display current readings from host hardware sensors.  
Periodic updates can be enabled for a readout message.  
Notifications about bot status.  

### Prerequisites
 * python 3.10
 * pip or anaconda env with python 3.10.6
 * Linux
 
Tested on Ubuntu 22 for now.
### install
For example, let's create new conda environment and install bot there
```
conda create -n mon_bot python=3.10.6
conda activate mon_bot
```
cd to repo directory and execute to install dependencies:
```
pip install -r ./requirements.txt
```

### Usage
Create configuration file named "config" inside bot_config directory
and set user parameters. Use this [example](bot_config/config_example) as reference.

Prerequisite notes:
* In order to use system control functionality, bot has to be run with sudo privilleges
* If you haven't done so, you have to install lm-sensors package and detect the required sensors
```
sudo apt install lm-sensors
sudo sensors-detect
```

Run module package monitor from the required environment, for example - from repo directory:
```
python -m monitor
```

### TODO
 * Add AMD gpu sensor monitor
 * Add mdstat monitor for raid arrays
 * Add comprehensive system info (load, uptime, hardware usage, hardware stats)

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
