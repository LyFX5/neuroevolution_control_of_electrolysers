


import numpy as np


class ControllerElectrolyser:
    def __init__(self):
        self.plan_granularity = 15 * 60
        self.hours_in_plan_horizon = 6
        self.Wsec_to_kWh_scale = 1 / 3600000

    def getAction_Manual(self):
        return list(map(float, input().split()))


    def form_control_signal(self, plant_state, reference_signal_plan):
        electrolyser_max_power = 2400
        electrolyser_min_percentage = 60
        electrolyser_max_percentage = 100
        switch_ON_threshold_coef = 0.4 # fit
        switch_OFF_threshold_coef = 0.4 # fit

        def is_permissible_to_switch_ON_elec():
            if plant_state["switch_num"] == 0: # fit
                unclaimed_power_plan_mean = np.mean(reference_signal_plan)
                if unclaimed_power_plan_mean >= switch_ON_threshold_coef * electrolyser_max_power: # fit
                    return True
            return False

        def is_permissible_to_switch_OFF_elec():
            unclaimed_power_plan_mean = np.mean(reference_signal_plan)
            if unclaimed_power_plan_mean < switch_OFF_threshold_coef * electrolyser_max_power:  # fit
                return True
            return False

        if plant_state["state"] == "steady":
            reference_power = min(electrolyser_max_power, reference_signal_plan[0])
            if (reference_power / electrolyser_max_power) < (electrolyser_min_percentage / 100):
                if (reference_power / electrolyser_max_power) < ((electrolyser_min_percentage / 2) / 100): # fit
                    if is_permissible_to_switch_OFF_elec():
                        reference_power = 0
                    else:
                        reference_power = electrolyser_max_power * electrolyser_min_percentage / 100
                else:
                    reference_power = electrolyser_max_power * electrolyser_min_percentage / 100
        elif plant_state["state"] == "idle":
            reference_power = 0
            if reference_signal_plan[0] > electrolyser_max_power * electrolyser_min_percentage / 100: # fit
                if is_permissible_to_switch_ON_elec():
                    reference_power = min(electrolyser_max_power, reference_signal_plan[0])
        else:
            reference_power = plant_state["target"] * electrolyser_max_power
        reference_percentage = 100 * reference_power / electrolyser_max_power
        return reference_percentage


    def form_control_signal_energy_based(self, plant_state, reference_signal_plan):
        electrolyser_max_power = 2400
        electrolyser_min_percentage = 60
        electrolyser_max_percentage = 100
        switch_ON_threshold_coef = 0.4 # fit
        switch_OFF_threshold_coef = 0.4 # fit
        elec_min_work_hours = 2 # fit

        def is_permissible_to_switch_ON_elec():
            if plant_state["switch_num"] == 0: # fit
                predicted_energy = np.sum(reference_signal_plan) * self.plan_granularity
                elec_min_energy = elec_min_work_hours * 3600 * \
                                      electrolyser_max_power * electrolyser_min_percentage / 100
                if predicted_energy > elec_min_energy: # fit
                    return True
            return False

        def is_permissible_to_switch_OFF_elec():
            predicted_energy = np.sum(reference_signal_plan) * self.plan_granularity
            elec_min_energy = elec_min_work_hours * 3600 * \
                              electrolyser_max_power * electrolyser_min_percentage / 100
            if predicted_energy <= elec_min_energy:  # fit
                return True
            return False

        if plant_state["state"] == "steady":
            reference_power = min(electrolyser_max_power, reference_signal_plan[0])
            if (reference_power / electrolyser_max_power) < (electrolyser_min_percentage / 100):
                if (reference_power / electrolyser_max_power) < ((electrolyser_min_percentage / 2) / 100): # fit
                    if is_permissible_to_switch_OFF_elec():
                        reference_power = 0
                    else:
                        reference_power = electrolyser_max_power * electrolyser_min_percentage / 100
                else:
                    reference_power = electrolyser_max_power * electrolyser_min_percentage / 100
        elif plant_state["state"] == "idle":
            reference_power = 0
            if reference_signal_plan[0] > electrolyser_max_power * (electrolyser_min_percentage/2) / 100: # fit
                if is_permissible_to_switch_ON_elec():
                    reference_power = max(electrolyser_min_percentage * electrolyser_max_power / 100,
                                          min(electrolyser_max_power, reference_signal_plan[0]))
        else:
            reference_power = plant_state["target"] * electrolyser_max_power
        reference_percentage = 100 * reference_power / electrolyser_max_power
        return reference_percentage

