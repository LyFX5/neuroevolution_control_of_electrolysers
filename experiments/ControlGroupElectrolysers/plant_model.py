from typing import List, Union
import numpy as np
from electrolyser_model import Electrolyser


class GroupOfElectrolysers:
    def __init__(self, number_of_electrolysers: int, sampling_time: float) -> None:
        self.__number_of_electrolysers: int = number_of_electrolysers
        self.__sampling_time: float = sampling_time
        self.__group: List = []
        for j in range(self.__number_of_electrolysers):
            self.__group.append(Electrolyser(elec_id = j, sampling_time = self.__sampling_time))

    def make_dynamical_step(self, u_group: np.ndarray) -> None:
        for j in range(self.__number_of_electrolysers):
            self.__group[j].step(u_group[j])
            
    @property
    def electrolyser_max_power(self) -> float:
        return self.__group[0].maxPower
            
    @property
    def number_of_electrolysers(self) -> int:
        return self.__number_of_electrolysers

    @property
    def sampling_time(self) -> float:
        return self.__sampling_time

    @property
    def group_state(self) -> List[Union[float, List]]:
        group_output: float = 0
        set_points = []
        outputs = []
        output_derives = []
        temperatures = []
        stack_states = []
        group_deterioration: List = []
        for j in range(self.__number_of_electrolysers):
            elec = self.__group[j]
            y = elec.output
            deterioration = elec.deterioration
            group_output += y
            set_points.append(elec.set_point)
            outputs.append(y)
            output_derives.append((y - elec.output_prev) / self.__sampling_time)
            temperatures.append(elec.temperature)
            stack_states.append(elec.electrolyser_stack_state)
            group_deterioration.append(deterioration)
        return [group_output,
                set_points,
                outputs,
                output_derives,
                temperatures,
                stack_states,
                group_deterioration]



# from electrolyser_detailed_model import Electrolyser


# class GroupOfElectrolysers:
#     def __init__(self, number_of_electrolysers: int, sampling_time: float) -> None:
#         self.__number_of_electrolysers: int = number_of_electrolysers
#         self.__sampling_time: float = sampling_time
#         self.__group: List = []
#         for j in range(self.__number_of_electrolysers):
#             self.__group.append(Electrolyser(ID=j, delta_t=self.__sampling_time))
#
#     def make_dynamical_step(self, u_group: np.ndarray) -> None:
#         for j in range(self.__number_of_electrolysers):
#             self.__group[j].apply_control_signal_in_moment(u_group[j])
#
#     @property
#     def number_of_electrolysers(self) -> int:
#         return self.__number_of_electrolysers
#
#     @property
#     def group_state(self) -> List[Union[float, List]]:
#         group_output: float = 0
#         set_points = []
#         outputs = []
#         output_derives = []
#         temperatures = []
#         stack_states = []
#         group_deterioration: List = []
#         for j in range(self.__number_of_electrolysers):
#             elec = self.__group[j]
#             y = elec.getDinamics()[0]
#             deterioration = elec.getRunOut()
#             group_output += y
#             set_points.append(elec.getCurrentTarget())
#             outputs.append(y)
#             output_derives.append(elec.getDinamics()[1])
#             temperatures.append(elec.getTemperatureDinamics()[0])
#             stack_states.append(elec.getState())
#             group_deterioration.append(deterioration)
#         return [group_output,
#                 set_points,
#                 outputs,
#                 output_derives,
#                 temperatures,
#                 stack_states,
#                 group_deterioration]



