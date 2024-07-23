from typing import List

import numpy as np
import pandas as pd


class ReferenceTrajectorySource:
    def __init__(self,
                 planing_horizon_in_seconds,
                 sampling_time_plan,
                 sampling_time_plant,
                 number_of_electrolysers,
                 electrolyser_max_power,
                 historical_data_path,
                 simulation_time_in_seconds):
        self.__dt = sampling_time_plant
        self.__Dt = sampling_time_plan
        self.__horizon = planing_horizon_in_seconds // self.__Dt
        self.__simulation_time = simulation_time_in_seconds
        assert self.__horizon == 24
        self.__number_of_electrolysers = number_of_electrolysers
        self.__electrolyser_max_power = electrolyser_max_power
        self.__plan = np.random.uniform(0.4, self.__number_of_electrolysers, self.__horizon)
        self.__historical_data_source = DataSource(historical_data_path)
        self.__plan_from_historical_data = None
        
    @property
    def plan_from_historical_data(self):
        return self.__plan_from_historical_data
    
    @property
    def sampling_time(self) -> float:
        return self.__Dt

    @property
    def preparing_plans(self) -> List:
        return self.__preparing_plans

    def prepare_plans(self):
        self.__preparing_plans = []
        plan = np.random.uniform(0.4, self.__number_of_electrolysers, self.__horizon)
        for i in range(int(self.__simulation_time // self.__Dt)):
            plan = np.delete(plan, 0, 0)
            plan = np.append(plan, np.random.uniform(0.4, self.__number_of_electrolysers, 1)[0])
            self.__preparing_plans.append(plan)

    def form_plan_from_preparing(self, instant):
        assert self.__preparing_plans is not None, f"{self.__preparing_plans=}"
        return self.__preparing_plans[int(instant * self.__dt // self.__Dt)]

    def form_plan(self, instant: int):
        if self.__plan_from_historical_data is not None:
            return self.form_plan_from_historical_data(instant)
        elif self.__preparing_plans is not None:
            return self.form_plan_from_preparing(instant)
        else:
            if int(instant * self.__dt) % int(self.__Dt) == 0:
                self.__plan = np.delete(self.__plan, 0, 0)
                self.__plan = np.append(self.__plan, np.random.uniform(0.4, self.__number_of_electrolysers, 1)[0])
            return self.__plan


    def get_full_plan_from_historical_data(self, year, month, day):
        self.__plan_from_historical_data = self.__historical_data_source.get_day_full_plan(year, month, day)
        if self.__plan_from_historical_data is not None:
            self.__plan_from_historical_data /= self.__electrolyser_max_power
            assert len(self.__plan_from_historical_data ) == ((self.__simulation_time / self.__Dt) + self.__horizon)
            self.__plan_from_historical_data = np.clip(self.__plan_from_historical_data, a_min=None, a_max=self.__number_of_electrolysers)

    def form_plan_from_historical_data(self, instant: int):
        assert self.__plan_from_historical_data is not None, f"Run get_full_plan_from_historical_data(year, month, day) first, pleas."
        assert len(self.__plan_from_historical_data ) == ((self.__simulation_time / self.__Dt) + self.__horizon)
        t = int(instant * self.__dt) // int(self.__Dt)
        return self.__plan_from_historical_data[t : t + self.__horizon]


class DataSource:
    def __init__(self, grid_power_time_series_path: str) -> None:
        self.__path = grid_power_time_series_path
        self.__grid_export_power_data_frame = self.__get_grid_export_power_data_frame(grid_power_time_series_path)

    def __get_grid_export_power_data_frame(self, grid_power_time_series_path: str) -> pd.DataFrame:
        tesla_df = pd.read_csv(grid_power_time_series_path)
        grid_power = tesla_df[['timestamp', 'grid_power']]
        grid_power['grid_power'].clip(lower=None, upper=0, inplace=True)
        grid_power['grid_power'] = -grid_power['grid_power']
        grid_power["timestamp"] = pd.to_datetime(grid_power["timestamp"])
        return grid_power

    def get_grid_export_power_data_slice(self, timestamp_start: pd.Timestamp, timedelta: pd.Timedelta):
        # get_data_slice(pd.Timestamp(2022, 6, 2, 7).tz_localize('UTC'), pd.Timedelta('12:00:00'))
        timestamp_end = timestamp_start + timedelta
        data_slice = self.__grid_export_power_data_frame.loc[(self.__grid_export_power_data_frame["timestamp"] > timestamp_start) & (self.__grid_export_power_data_frame["timestamp"] < timestamp_end)]
        if data_slice.isna().values.any():
            print("The day has NaN values! Chose another day, pleas.")
            return None
        return data_slice

    def change_granularity_1_to_15_minutes(self, array: np.ndarray):
        N = len(array) // 15
        array_new = []
        for i in range(N):
            array_new.append(np.mean(array[i * 15: (i + 1) * 15]))
        return np.array(array_new)

    def get_day_full_plan(self, year, month, day):
        timestamp_start = pd.Timestamp(year, month, day, 7).tz_localize('UTC')
        timedelta = pd.Timedelta('18:00:00')
        data_slice = self.get_grid_export_power_data_slice(timestamp_start, timedelta)
        if data_slice is None:
            return None
        day_grid_power_export_array = data_slice['grid_power'].to_numpy()
        if len(day_grid_power_export_array) != 18 * 60:
            return None
        day_grid_power_export_array_15_minutes = self.change_granularity_1_to_15_minutes(day_grid_power_export_array)
        return day_grid_power_export_array_15_minutes


