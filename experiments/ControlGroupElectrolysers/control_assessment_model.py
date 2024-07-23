# import matplotlib.pyplot as plt
import numpy as np

class ControlAssessment:
    def __init__(self, sample_time_plant, electrolyser_max_power):
        self.__q1 = 1 # in [0, 1]
        self.__q2 = 1 # 0.3 # in [0, 1]
        self.__q3 = 0.05 # in [0, 1]
        self.__control_system_sample_time = sample_time_plant
        self.__scale_factor = electrolyser_max_power
        
    def cost(self,
             trajectory_reference: np.ndarray,
             trajectory: np.ndarray,
             group_deterioration: np.ndarray,
             control_strategy: np.ndarray) -> float:
        H = len(trajectory)
        control_strategy_length = len(control_strategy) - 1
        error = trajectory_reference - trajectory
        J_y = np.dot(error, error) / H
        J_u = sum([np.dot((control_strategy[T+1] - control_strategy[T]), (control_strategy[T+1] - control_strategy[T])) for T in range(control_strategy_length)]) / control_strategy_length
        gdm = np.mean(group_deterioration)
        J_d = np.dot(group_deterioration-gdm, group_deterioration-gdm) / len(group_deterioration)
        Cost_episode = self.__q1 * J_y + self.__q2 * J_u + self.__q3 * J_d
        return Cost_episode

    def show_results(self,
                     trajectory_reference: np.ndarray,
                     trajectory: np.ndarray,
                     group_deterioration: np.ndarray,
                     control_strategy: np.ndarray) -> list[float]:
        H = len(trajectory)
        control_strategy_length = len(control_strategy) - 1
        error = trajectory_reference - trajectory
        J_y = np.dot(error, error) / H
        J_u = sum([np.dot((control_strategy[T+1] - control_strategy[T]), (control_strategy[T+1] - control_strategy[T])) for T in range(control_strategy_length)]) / control_strategy_length
        gdm = np.mean(group_deterioration)
        J_d = np.dot(group_deterioration-gdm, group_deterioration-gdm) / len(group_deterioration)
        Cost_episode = self.__q1 * J_y + self.__q2 * J_u + self.__q3 * J_d
        RMSE = np.sqrt(J_y)
        N = np.absolute(error)
        D = np.absolute(trajectory_reference) + np.absolute(trajectory)
        N = N[D != 0]
        D = D[D != 0]
        SMAPE = 0
        MAE = 0
        if N.size > 0:
            SMAPE = np.mean(np.divide(N, D))
            MAE = np.mean(N)
        unclaimed_energy = np.sum(trajectory_reference) * self.__scale_factor * self.__control_system_sample_time / 3_600_000 # kW * h
        consumed_energy = np.sum(trajectory) * self.__scale_factor * self.__control_system_sample_time / 3_600_000 # kW * h
        return [Cost_episode, RMSE, J_y, J_u, J_d, MAE, SMAPE, unclaimed_energy, consumed_energy]


