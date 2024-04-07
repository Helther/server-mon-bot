import psutil
import pynvml
from monitor.bot_utils import logger


def get_nvidia_temps() -> dict:
    temps = {}
    try:
        pynvml.nvmlInit()
        deviceCount = pynvml.nvmlDeviceGetCount()
        for i in range(deviceCount):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            name = pynvml.nvmlDeviceGetName(handle)
            if name:
                temps[name] = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
        pynvml.nvmlShutdown()
    except:
        logger.warning("get_nvidia_temps: NVidia library failed to initialize")
    return temps


def get_gpu_temps() -> dict:
    return get_nvidia_temps()  # TODO add Radeon


def gpu_temps_to_str(data: dict) -> str:
    res = ""
    if not data:
        return res

    for name, value in data.items():
        res += f"   {name}  <b>{value}</b>°C\n"

    if res:
        res = "GPU Temperatures:\n" + res

    return res


def get_sensors_temperatures() -> dict:
    return psutil.sensors_temperatures() if hasattr(psutil, "sensors_temperatures") else {}


def temperatures_to_str(sensors_data: dict) -> str:
    if not sensors_data:
        return "can't read any temperature info"

    res = "Temperatures:\n"
    names = set(list(sensors_data.keys()))
    for name in names:
        res += f"\n    {name}\n"
        if name in sensors_data:
            for entry in sensors_data[name]:
                s = "       %-40s <b>%s</b>°C\n" % (
                    entry.label or name,
                    entry.current
                )
                res += s
    return res


def get_sensors_fan_speeds() -> dict:
    fans = psutil.sensors_fans() if hasattr(psutil, "sensors_fans") else {}
    return fans


def get_gpu_fans() -> dict:
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
                    fans.append(pynvml.nvmlDeviceGetFanSpeed_v2(handle, fan_i))
                data[name] = fans
        pynvml.nvmlShutdown()
    except:
        logger.warning("get_gpu_fans: NVidia library failed to initialize")
    return data


def gpu_fans_to_str(data: dict[str, list]) -> str:
    res = ""
    if not data:
        return res

    for name, value in data.items():
        res += f"   {name}\n"
        for i, fan in enumerate(value):
            res += "        fan%-40s <b>%s</b> %s\n" % (i, fan, '%')

    if res:
        res = "GPU Fans:\n" + res

    return res


def fans_to_str(data: dict) -> str:
    if not data:
        return "can't read any fans info"
        
    res = "Fans speeds:\n"
    names = set(list(data.keys()))
    for name in names:
        res += f"\n   {name}\n"
        if name in data:
            for entry in data[name]:
                s = "        %-40s <b>%s</b> RPM\n" % (entry.label or name, entry.current)
                res += s
    return res
