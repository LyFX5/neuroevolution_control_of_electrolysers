import numpy as np
# import copy
from plant_model import GroupOfElectrolysers


class ControllerHeuristic:    
    def __init__(self, planing_horizon, sampling_time_control, sampling_time_plant, sampling_time_plan):
        self.__sampling_time_plant: int = sampling_time_plant
        self.__sampling_time_plan: int = sampling_time_plan # self.plan_granularity = 15 * 60
        self.__sampling_time_control: int = sampling_time_control
        assert (self.__sampling_time_control >= self.__sampling_time_plan) and (self.__sampling_time_control % self.__sampling_time_plan == 0), f"The sampling_time_control mast be multiple of the sampling_time_plan!"
        self.__Wsec_to_kWh_scale = 1 / 3_600_000
        self.__eps = 0.5
        self.__set_point_max = 1
        self.__set_point_min = 0.6
    
    def form_control_signal(self,
                            instant: int,
                            plant_model_copy: GroupOfElectrolysers,
                            plan: np.ndarray) -> np.ndarray:
        '''
        ГРУППА ЭЛЕКТРОЛИЗЁРОВ ХРАНИТСЯ В СТРУКТУРЕ С ПОРЯДКОМ, А НЕ, НАПРИМЕР, В set!
        '''
        [group_output,
         set_points,
         outputs,
         output_derives,
         temperatures,
         stack_states,
         group_deterioration] = plant_model_copy.group_state
        control_signal = np.array(set_points) * 1.
        assert all([(0.6 <= control_signal[j] <= 1 or control_signal[j] == 0) for j in range(len(control_signal))])
        group_set_point_desired = np.mean(plan[:int(self.__sampling_time_control // self.__sampling_time_plan)])
        while abs(group_set_point_desired - control_signal.sum()) > self.__eps:
            error = group_set_point_desired - control_signal.sum()
            electrolysers_on = list(map(lambda x: 1 if x > 0 else 0, control_signal))
            electrolysers_on_60 = list(map(lambda x: 1 if abs(x - self.__set_point_min) < 0.000001 else 0, control_signal))
            electrolysers_on_100 = list(map(lambda x: 1 if abs(x - self.__set_point_max) < 0.000001 else 0, control_signal))
            ## iterate control_signal
            if error < 0: # group output is greater than reference group output
                assert sum(electrolysers_on) > 0, f"error < 0 and sum(electrolysers_on) <= 0. {electrolysers_on=}"
                if sum(electrolysers_on_60) < sum(electrolysers_on): # не все опущены на 0.6
                    error_abs = abs(error)
                    for j in range(len(control_signal)): # decreasing group output
                        if control_signal[j] > 0: # the same as electrolysers_on[j] == 1
                            control_signal[j] = max(self.__set_point_min, (control_signal[j] - error_abs / sum(electrolysers_on)))
                else: # все опущены на 0.6 значит придется кого-то выключить. выключам того, кто меньше всех переключался
                    index_of_the_less_used_switchedon_elec = None
                    for j in range(len(control_signal)):
                        if electrolysers_on_60[j] == 1: # the same electrolysers_on[j] == 1
                            index_of_the_less_used_switchedon_elec = j
                            break
                    assert index_of_the_less_used_switchedon_elec is not None
                    deterioration_min = group_deterioration[index_of_the_less_used_switchedon_elec]
                    for j in range(len(control_signal)):
                        if electrolysers_on_60[j] == 1: # the same electrolysers_on[j] == 1
                            if group_deterioration[j] < deterioration_min:
                                deterioration_min = group_deterioration[j]
                                index_of_the_less_used_switchedon_elec = j
                    # TODO добавить проверку, стоит ли его выключать и по такому ли принципу выбирать, кого выключать (анализировать план на будущее)
                    control_signal[index_of_the_less_used_switchedon_elec] = 0.
            else: # group output is less or equal than reference group output
                if sum(electrolysers_on_100) < sum(electrolysers_on): # есть те, кто включен, но еще может увеличить выход
                    assert sum(electrolysers_on) > 0, f"sum(electrolysers_on) <= 0. {electrolysers_on=}"
                    for j in range(len(control_signal)): # increasing group output
                        if control_signal[j] > 0: # the same as electrolysers_on[j] == 1
                            control_signal[j] = min(self.__set_point_max, (control_signal[j] + error / sum(electrolysers_on)))
                else: # значит придется кого-то включить. включам того, кто меньше всех переключался
                    index_of_the_less_used_switchedoff_elec = None
                    for j in range(len(control_signal)):
                        if electrolysers_on[j] == 0:
                            index_of_the_less_used_switchedoff_elec = j
                            break
                    assert index_of_the_less_used_switchedoff_elec is not None
                    deterioration_min = group_deterioration[index_of_the_less_used_switchedoff_elec]
                    for j in range(len(control_signal)):
                        if electrolysers_on[j] == 0:
                            if group_deterioration[j] < deterioration_min:
                                deterioration_min = group_deterioration[j]
                                index_of_the_less_used_switchedoff_elec = j
                    # TODO добавить проверку, стоит ли его включать и по такому ли принципу выбирать, кого включать (анализировать план на будущее)
                    control_signal[index_of_the_less_used_switchedoff_elec] = 0.6
        return control_signal

    def form_control_signal_random_on_off(self,
                            instant: int,
                            plant_model_copy: GroupOfElectrolysers,
                            plan: np.ndarray) -> np.ndarray:
        [group_output,
         set_points,
         outputs,
         output_derives,
         temperatures,
         stack_states,
         group_deterioration] = plant_model_copy.group_state
        control_signal = np.array(set_points) * 1.
        group_set_point_desired = plan[0]
        while abs(group_set_point_desired - control_signal.sum()) > self.__eps:
            error = group_set_point_desired - control_signal.sum()
            electrolysers_on = []
            electrolysers_off = []
            for j in range(len(control_signal)):
                if control_signal[j] > 0:
                    electrolysers_on.append(j)
                else:
                    electrolysers_off.append(j)
            ## iterate control_signal
            if error < 0: # group output is greater than reference group output
                control_signal[np.random.choice(electrolysers_on)] = 0.
            else: # group output is less or equal than reference group output
                control_signal[np.random.choice(electrolysers_off)] = 1.
        return control_signal
    
#     def form_control_signal_energy_based(self, plant_state, reference_signal_plan):
#         electrolyser_max_power = 2400
#         electrolyser_min_percentage = 60
#         electrolyser_max_percentage = 100
#         switch_ON_threshold_coef = 0.4 # fit
#         switch_OFF_threshold_coef = 0.4 # fit
#         elec_min_work_hours = 2 # fit

#         def is_permissible_to_switch_ON_elec():
#             if plant_state["switch_num"] == 0: # fit
#                 predicted_energy = np.sum(reference_signal_plan) * self.plan_granularity
#                 elec_min_energy = elec_min_work_hours * 3600 * \
#                                       electrolyser_max_power * electrolyser_min_percentage / 100
#                 if predicted_energy > elec_min_energy: # fit
#                     return True
#             return False

#         def is_permissible_to_switch_OFF_elec():
#             predicted_energy = np.sum(reference_signal_plan) * self.plan_granularity
#             elec_min_energy = elec_min_work_hours * 3600 * \
#                               electrolyser_max_power * electrolyser_min_percentage / 100
#             if predicted_energy <= elec_min_energy:  # fit
#                 return True
#             return False

#         if plant_state["state"] == "steady":
#             reference_power = min(electrolyser_max_power, reference_signal_plan[0])
#             if (reference_power / electrolyser_max_power) < (electrolyser_min_percentage / 100):
#                 if (reference_power / electrolyser_max_power) < ((electrolyser_min_percentage / 2) / 100): # fit
#                     if is_permissible_to_switch_OFF_elec():
#                         reference_power = 0
#                     else:
#                         reference_power = electrolyser_max_power * electrolyser_min_percentage / 100
#                 else:
#                     reference_power = electrolyser_max_power * electrolyser_min_percentage / 100
#         elif plant_state["state"] == "idle":
#             reference_power = 0
#             if reference_signal_plan[0] > electrolyser_max_power * (electrolyser_min_percentage/2) / 100: # fit
#                 if is_permissible_to_switch_ON_elec():
#                     reference_power = max(electrolyser_min_percentage * electrolyser_max_power / 100,
#                                           min(electrolyser_max_power, reference_signal_plan[0]))
#         else:
#             reference_power = plant_state["target"] * electrolyser_max_power
#         reference_percentage = 100 * reference_power / electrolyser_max_power
#         return reference_percentage
    


