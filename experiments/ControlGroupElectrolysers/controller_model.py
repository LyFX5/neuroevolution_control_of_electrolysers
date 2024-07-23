import numpy as np
from plant_model import GroupOfElectrolysers

class Controller:
    def __init__(self, policy, control_signal_dimension: int, sampling_time_control: float):
        self.__policy = policy
        self.__control_signal_dimension = control_signal_dimension
        self.__sampling_time = sampling_time_control

    @property
    def sampling_time(self) -> float:
        return self.__sampling_time

    def form_control(self, instant: int, plant: GroupOfElectrolysers, plan: np.ndarray) -> np.ndarray:
        return self.__policy(instant, plant, plan, self.__control_signal_dimension)


