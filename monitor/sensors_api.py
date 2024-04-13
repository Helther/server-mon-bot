import psutil
import pynvml
from monitor.bot_utils import logger


class Sensor:
    def __init__(self, name: str, label: str, value: float, units: str) -> None:
        self.name: str = name
        self.label: str = label
        self.value: float = value
        self.units: str = units

    def __str__(self) -> str:
        return "       %-40s <b>%s</b>%s\n" % (
                    self.label or self.name,
                    self.value,
                    self.units
                )

    def config_name(self) -> str:
        return f"{self.name}.{self.label}"


def get_nvidia_temps() -> dict[str, Sensor]:
    temps = {}
    try:
        pynvml.nvmlInit()
        deviceCount = pynvml.nvmlDeviceGetCount()
        for i in range(deviceCount):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            name = pynvml.nvmlDeviceGetName(handle)
            if name:
                temps[name] = (Sensor(name, name, pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU), "°C"))
        pynvml.nvmlShutdown()
    except:
        logger.warning("get_nvidia_temps: NVidia library failed to initialize")
    return temps


def get_gpu_temps() -> dict:
    return get_nvidia_temps()  # TODO add Radeon


def gpu_temps_to_str(data: dict[str, Sensor]) -> str:
    res = ""
    if not data:
        return "can't read any GPU info"

    for value in data.values():
        res += str(value)

    if res:
        res = "GPU Temperatures:\n" + res

    return res


def get_sensors_temperatures() -> dict[str, Sensor]:
    sensors_data = psutil.sensors_temperatures() if hasattr(psutil, "sensors_temperatures") else {}
    names = set(list(sensors_data.keys()))
    res = {}
    for name in names:
        counter = 0
        for entry in sensors_data[name]:
            s = Sensor(name, entry.label or name + f"_{counter}", entry.current, "°C")
            res[s.config_name()] = s
            counter += 1

    return res


def temperatures_to_str(sensors_data: dict[str, Sensor]) -> str:
    if not sensors_data:
        return "can't read any temperature info"

    res = "Temperatures:\n"
    last_name = None
    for sensor in sensors_data.values():
        if not last_name or last_name != sensor.name:
            last_name = sensor.name
            res += f"\n    {sensor.name}\n"
        res += str(sensor)
    return res


def get_sensors_fan_speeds() -> dict[str, Sensor]:
    data = psutil.sensors_fans() if hasattr(psutil, "sensors_fans") else {}
    res = {}
    names = set(list(data.keys()))
    for name in names:
        if name in data:
            counter = 0
            for entry in data[name]:
                s = Sensor(name, entry.label or name + f"_{counter}", entry.current, "RPM")
                res[s.config_name()] = s
                counter += 1
    return res


def fans_to_str(data: dict[str, Sensor]) -> str:
    if not data:
        return "can't read any fans info"
        
    res = "Fans speeds:\n"
    last_name = None
    for sensor in data.values():
        if not last_name or last_name != sensor.name:
            last_name = sensor.name
            res += f"\n    {sensor.name}\n"
        res += str(sensor)
    return res


def get_gpu_fans() -> dict[str, Sensor]:
    data = {}
    try:
        pynvml.nvmlInit()
        deviceCount = pynvml.nvmlDeviceGetCount()
        for i in range(deviceCount):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            name = pynvml.nvmlDeviceGetName(handle)
            if name:
                fans = []
                for fan_i in range(pynvml.nvmlDeviceGetNumFans(handle)):
                    s = Sensor(name, f"fan{fan_i}", pynvml.nvmlDeviceGetFanSpeed_v2(handle, fan_i), "%")
                    data[s.config_name()] = s
        pynvml.nvmlShutdown()
    except:
        logger.warning("get_gpu_fans: NVidia library failed to initialize")
    return data


def gpu_fans_to_str(data: dict[str, Sensor]) -> str:
    res = ""
    if not data:
        return res

    last_name = None
    for sensor in data.values():
        if not last_name or last_name != sensor.name:
            last_name = sensor.name
            res += f"\n    {sensor.name}\n"
        res += str(sensor)

    if res:
        res = "GPU Fans:\n" + res

    return res

def get_all_sensors() -> dict[str, Sensor]:
    res = get_sensors_fan_speeds()
    res |= get_sensors_temperatures()
    res |= get_gpu_temps()
    res |= get_gpu_fans()
    return res