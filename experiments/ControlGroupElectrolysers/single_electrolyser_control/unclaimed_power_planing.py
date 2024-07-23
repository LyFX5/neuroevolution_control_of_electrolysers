import numpy as np
import copy
import pandas as pd
from enum import Enum


class PlanTypes(Enum):
    RANDOM = "random"
    IDEAL = "ideal"
    FORECAST = "forecast"


class UnclaimedPowerSource:
    def __init__(self, unclaimed_power_maximal = 2400, plan_type: PlanTypes = PlanTypes.RANDOM):
        self.unclaimed_power_maximal = unclaimed_power_maximal # W
        self.unclaimed_power_plan_on_step = None
        self.plan_type = plan_type
        self.hours_in_plan_horizon = 6
        self.plan_granularity = 15 * 60
        self.plan_length = self.hours_in_plan_horizon * 3600 // self.plan_granularity

    # def generate_unclaimed_power_plan_on_step(self, current_step, time_step):
    #     # TODO не правильно форекаст имитируется (24 15минутки)
    #     simulation_current_time = current_step * time_step
    #     if (simulation_current_time % (15 * 60)) == 0:
    #         if self.plan_type == "random":
    #             self.unclaimed_power_plan_on_step = self.unclaimed_power_maximal * np.random.rand(self.plan_length)
    #         elif self.plan_type == "ideal":
    #             if (current_step % self.plan_length) == 0:
    #                 self.unclaimed_power_plan_on_step = self.unclaimed_power_maximal * np.random.rand(self.plan_length)
    #             else:
    #                 self.unclaimed_power_plan_on_step = np.delete(self.unclaimed_power_plan_on_step, 0)
    #                 self.unclaimed_power_plan_on_step = np.append(self.unclaimed_power_plan_on_step, [np.random.rand()])
    #         else:
    #             assert False, f"Incorrect plan type: {self.plan_type}"
    #     return self.unclaimed_power_plan_on_step



class UnclaimedPowerSourceHistoryBased(UnclaimedPowerSource):
    def __init__(self,
                 h2_power_data_frame: pd.DataFrame,
                 unclaimed_power_maximal = 2400,
                 plan_type: PlanTypes = PlanTypes.RANDOM):
        super(UnclaimedPowerSourceHistoryBased, self).__init__(unclaimed_power_maximal, plan_type)
        # TODO assert that h2_power_data_frame format is correct
        self.h2_power_data_frame = h2_power_data_frame
        self.h2_np_arr = None
        self.h2_np_arr_aggregated = None
        self.h2_power_data_frame_granularity = (h2_power_data_frame["timestamp"][1] -
                                                h2_power_data_frame["timestamp"][0]).value // 1000000000

    def setup_simulation_episode(self, start_timestamp, hours_in_episode):
        hours = hours_in_episode + self.hours_in_plan_horizon
        time_delta = pd.Timedelta(hours=hours, minutes=0, seconds=0)
        stop_timestamp = start_timestamp + time_delta
        episode_data = self.h2_power_data_frame.query(
            'timestamp >= @start_timestamp and timestamp < @stop_timestamp')
        self.h2_np_arr = episode_data.h2_power.to_numpy()
        self.h2_np_arr_aggregated = []
        number_of_values_for_aggregation = self.plan_granularity // self.h2_power_data_frame_granularity
        number_of_steps_in_plan = len(self.h2_np_arr) * self.h2_power_data_frame_granularity // self.plan_granularity
        for i in range(number_of_steps_in_plan):
            average = np.mean(self.h2_np_arr[i * number_of_values_for_aggregation :
                                             (i+1) * number_of_values_for_aggregation])
            self.h2_np_arr_aggregated.append(average)
        self.h2_np_arr_aggregated = np.array(self.h2_np_arr_aggregated)

    def generate_unclaimed_power_plan_on_step_from_history(self, current_step, simulation_discretization_interval):
        simulation_current_time = current_step * simulation_discretization_interval
        plan_step_number = simulation_current_time // self.plan_granularity
        if (simulation_current_time % self.plan_granularity) == 0:
            if self.plan_type == PlanTypes.RANDOM:
                assert False, f"Incorrect plan type: {self.plan_type}"
            elif self.plan_type == PlanTypes.IDEAL:
                self.unclaimed_power_plan_on_step = self.h2_np_arr_aggregated[plan_step_number :
                                                                              plan_step_number + self.plan_length]
            else:
                assert False, f"Incorrect plan type: {self.plan_type}"
        return self.unclaimed_power_plan_on_step
