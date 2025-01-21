import sounddevice as sd

Talking = True

print("Default devices: In:", sd.default.device[0], "Out:", sd.default.device[1])
print("All devices:\n", sd.query_devices(device=None, kind=None))