from enum import Enum, auto
import numpy as np


class ElectrolyserCore():
    class States(Enum):
        IDLE = 0
        HEATING = auto()
        HYDRATION = auto()
        RAMP_UP_1 = auto()
        RAMP_UP_2 = auto()
        STEADY = auto()
        RAMP_DOWN_1 = auto()
        RAMP_DOWN_2 = auto()
        OFFLINE = auto()
        INCORRECT = auto()

    class Param2Idx(Enum):
        Y = 0
        YD = auto()
        YDD = auto()
        Y_MAX = auto()
        TEMPERATURE = auto()
        TEMPERATURE_D = auto()
        TEMPERATURE_WHEN_RAMPUP2_STARTS = auto()
        HYDRATION_START = auto()
        TOTAL_RUN_OUT_NEW = auto()
        SWITCH_NUM = auto()
        TIME = auto()
        CONST = auto()

    CTR_COEF = 1.097
    IDLE_PRODUCTION_RATE = 0
    LOWER_PRODUCTION_RATE = 0.6
    UPPER_PRODUCTION_RATE = 1
    HYDRATION_DURATION = 62
    STEADY_REACT_SPEED = 1 / 55
    STATE_VECTOR_SIZE = 12
    TEMPER_CTR_COEF = 1
    TEMPER_CTR_COEF_HEATING = 1
    TIME_STEP = 1
    T_RAMP_UP_2_SCALER = 1 / 500
    T_RAMP_DOWN_1_SCALER = 1 / 20
    T_RAMP_DOWN_2_SCALER = 1 / 30
    T_TEMPER_IDLE_SCALER = 1 / 14000
    T_TEMPER_HEATING_SCALER = 1 / 700
    T_TEMPER_HYDRATION_SCALER = 1 / 3500
    T_TEMPER_RAMP_UP_1_SCALER = 1 / 3500
    T_TEMPER_RAMP_DOWN_1_SCALER = 1 / 4000
    T_TEMPER_RAMP_UP_2_SCALER = 1 / 3500
    T_TEMPER_RAMP_DOWN_2_SCALER = 1 / 4000
    T_TEMPER_STEADY_LOW_SCALER = 1 / 3500
    T_TEMPER_STEADY_HIGH_SCALER = 1 / 200
    RAMP_DOWN_A_SCALER = 500
    RAMP_UP_1_A0 = 0.000225
    RAMP_UP_1_A1 = 0.03
    RAMP_UP_1_B0 = 0.000225
    RAMP_UP_1_B1 = -22 * 0.000225
    RAMP_UP_1_SWITCH_STEP = 0.08
    RAMP_UP_DYNAMIC_CHANGE_BORDER = 0.11
    RAMP_DOWN_DYNAMIC_CHANGE_BORDER = 0.5
    RAMP_DOWN_FINISH_BORDER = 0.1
    STATES_LABELS = (
            "idle",
            "heating",
            "hydration",
            "ramp_up_1",
            "ramp_up_2",
            "steady",
            "ramp_down_1",
            "ramp_down_2",
            "offline",
            "incorrect",
        )
    maxPower = 2400
    maxCurrent = 53
    pr_epsilon = 0.01
    allowed_delta_t_max: float = 5
    allowed_delta_t_min: float = 1

    def __init__(self, ident, delta_t):
        self.ident: str = ident
        self.state: ElectrolyserCore.States = ElectrolyserCore.States.IDLE
        assert (ElectrolyserCore.allowed_delta_t_min <= delta_t <= ElectrolyserCore.allowed_delta_t_max), \
            f"delta_t must be in range {ElectrolyserCore.allowed_delta_t_min} ... {ElectrolyserCore.allowed_delta_t_max}"
        self.delta_t = delta_t
        self.envTemperature = 30.0
        self.maxTemperature = 54.2
        self.minTemperature = 21.0
        self.cost_of_work_for_a_delta_t = 0.1 # = power_consumption
        self.run_out_in_delta_t_new = self.delta_t / 3600 # H
        self.run_out_of_switchOn_new = 0.683 # H
        self.run_out_of_switchOff_new = 0.683 # H
        self.allowed_switch_num = 2
        self.target = 0
        self.u_log = [] # лог управляющих воздействий применяющихся к электролизеру
        self.vector = np.zeros((self.STATE_VECTOR_SIZE, 1), dtype=float)
        self.vector[self.Param2Idx.CONST.value] = 1
        self.vector[self.Param2Idx.TEMPERATURE.value] = 22
        self.transf_matrix = self.make_empty_transf_martix()
        self.U = 0

    def make_empty_transf_martix(self) -> np.ndarray:
        return np.zeros((self.STATE_VECTOR_SIZE, self.STATE_VECTOR_SIZE), dtype=float)

    def apply_signal(self, U: float) -> None:
        self.prepare_for_apply_signal(self.transf_matrix, U)
        self.vector = np.matmul(self.transf_matrix, self.vector)

    def prepare_for_apply_signal(self, transf_matrix: np.ndarray, U: float) -> None:
        assert not ((self.IDLE_PRODUCTION_RATE < U < self.LOWER_PRODUCTION_RATE) or U < self.IDLE_PRODUCTION_RATE or U > self.UPPER_PRODUCTION_RATE)
        self.U = U
        transf_matrix.fill(0)
        transf_matrix[range(self.STATE_VECTOR_SIZE), range(self.STATE_VECTOR_SIZE)] = 1
        transf_matrix[self.Param2Idx.TIME.value, self.Param2Idx.CONST.value] = self.delta_t if not self.state == self.States.IDLE else 0
        transf_matrix[self.Param2Idx.TOTAL_RUN_OUT_NEW.value, self.Param2Idx.CONST.value] = self.run_out_in_delta_t_new if not self.state == self.States.IDLE else 0
        transf_matrix[self.Param2Idx.CONST.value, self.Param2Idx.CONST.value] = 1
        if self.state == self.States.IDLE:
            self.__idle_handler(transf_matrix, U)
        elif self.state == self.States.HEATING:
            self.__heating_handler(transf_matrix, U)
        elif self.state == self.States.HYDRATION:
            self.__hydration_handler(transf_matrix, U)
        elif self.state == self.States.RAMP_UP_1:
            self.__ramp_up_1_handler(transf_matrix, U)
        elif self.state == self.States.RAMP_UP_2:
            self.__ramp_up_2_handler(transf_matrix, U)
        elif self.state == self.States.STEADY:
            self.__steady_handler(transf_matrix, U)
        elif self.state == self.States.RAMP_DOWN_1:
            self.__ramp_down_1_handler(transf_matrix, U)
        elif self.state == self.States.RAMP_DOWN_2:
            self.__ramp_down_2_handler(transf_matrix, U)
        else:
            self.__incorrect_handler(transf_matrix, U)
        np.copyto(self.transf_matrix, transf_matrix)

    def __idle_handler(self,transf_matrix: np.ndarray,  U: float):
        self.target = U
        transf_matrix[self.Param2Idx.Y.value, self.Param2Idx.Y.value] = 0
        transf_matrix[self.Param2Idx.YD.value, self.Param2Idx.YD.value] = 0
        transf_matrix[self.Param2Idx.YDD.value, self.Param2Idx.YDD.value] = 0
        transf_matrix[self.Param2Idx.TEMPERATURE.value, self.Param2Idx.TEMPERATURE_D.value] = self.delta_t
        transf_matrix[self.Param2Idx.TEMPERATURE_D.value, self.Param2Idx.TEMPERATURE.value] = -1
        transf_matrix[self.Param2Idx.TEMPERATURE_D.value, self.Param2Idx.TEMPERATURE_D.value] = -self.delta_t
        transf_matrix[self.Param2Idx.TEMPERATURE_D.value, self.Param2Idx.CONST.value] =  self.TEMPER_CTR_COEF * self.envTemperature
        transf_matrix[self.Param2Idx.TEMPERATURE_D.value] *= self.T_TEMPER_IDLE_SCALER
        transf_matrix[self.Param2Idx.TOTAL_RUN_OUT_NEW.value, self.Param2Idx.TOTAL_RUN_OUT_NEW.value] = 0
        transf_matrix[self.Param2Idx.TOTAL_RUN_OUT_NEW.value, self.Param2Idx.CONST.value] = 0
        if self.target > 0:
            transf_matrix[self.Param2Idx.TIME.value, self.Param2Idx.TIME.value] = 0
            transf_matrix[self.Param2Idx.TOTAL_RUN_OUT_NEW.value, self.Param2Idx.TOTAL_RUN_OUT_NEW.value] = 1
            transf_matrix[self.Param2Idx.TOTAL_RUN_OUT_NEW.value][self.Param2Idx.CONST.value] = self.run_out_of_switchOn_new
            transf_matrix[self.Param2Idx.SWITCH_NUM.value][self.Param2Idx.CONST.value] = 1
            if self.vector[self.Param2Idx.TEMPERATURE.value] < self.minTemperature:
                self.state = self.States.HEATING
            else:
                self.state = self.States.HYDRATION
                transf_matrix[self.Param2Idx.HYDRATION_START.value, self.Param2Idx.HYDRATION_START.value] = 0
                transf_matrix[self.Param2Idx.HYDRATION_START.value, self.Param2Idx.CONST.value] = np.dot(transf_matrix[self.Param2Idx.TIME.value], self.vector)
        self.u_log.append(0)

    def __heating_handler(self,transf_matrix: np.ndarray,  U: float):
        transf_matrix[self.Param2Idx.Y.value, self.Param2Idx.Y.value] = 0
        transf_matrix[self.Param2Idx.YD.value, self.Param2Idx.YD.value] = 0
        transf_matrix[self.Param2Idx.YDD.value, self.Param2Idx.YDD.value] = 0
        transf_matrix[self.Param2Idx.TEMPERATURE.value, self.Param2Idx.TEMPERATURE_D.value] = self.delta_t
        transf_matrix[self.Param2Idx.TEMPERATURE_D.value, self.Param2Idx.TEMPERATURE_D.value] =  0
        transf_matrix[self.Param2Idx.TEMPERATURE_D.value, self.Param2Idx.CONST.value] =  self.maxTemperature * self.T_TEMPER_HEATING_SCALER
        if self.vector[self.Param2Idx.TEMPERATURE.value, 0] >= self.minTemperature:
            self.state = self.States.HYDRATION
            transf_matrix[self.Param2Idx.HYDRATION_START.value, self.Param2Idx.HYDRATION_START.value] = 0
            transf_matrix[self.Param2Idx.HYDRATION_START.value, self.Param2Idx.CONST.value] = self.time
        self.u_log.append(0)

    def __hydration_handler(self,transf_matrix: np.ndarray,  U: float):
        transf_matrix[self.Param2Idx.Y.value, self.Param2Idx.Y.value] = 0
        transf_matrix[self.Param2Idx.YD.value, self.Param2Idx.YD.value] = 0
        transf_matrix[self.Param2Idx.YDD.value, self.Param2Idx.YDD.value] = 0
        transf_matrix[self.Param2Idx.TEMPERATURE.value, self.Param2Idx.TEMPERATURE_D.value] = self.delta_t
        transf_matrix[self.Param2Idx.TEMPERATURE_D.value, self.Param2Idx.TEMPERATURE_D.value] = 0
        transf_matrix[self.Param2Idx.TEMPERATURE_D.value, self.Param2Idx.CONST.value] =  self.maxTemperature * self.T_TEMPER_HYDRATION_SCALER
        if self.time - self.hydration_start >= self.HYDRATION_DURATION:
            self.state = self.States.RAMP_UP_1
        self.u_log.append(0)

    def __ramp_up_1_handler(self,transf_matrix: np.ndarray,  U: float):
        transf_matrix[self.Param2Idx.YD.value, self.Param2Idx.YDD.value] = self.delta_t
        if self.production_rate == 0:
            transf_matrix[self.Param2Idx.Y.value, self.Param2Idx.Y.value] = 0
            transf_matrix[self.Param2Idx.Y.value, self.Param2Idx.CONST.value] = self.RAMP_UP_1_SWITCH_STEP * self.target
            transf_matrix[self.Param2Idx.YDD.value, self.Param2Idx.CONST.value] = -self.RAMP_UP_1_A0 * self.RAMP_UP_1_SWITCH_STEP * self.target
            transf_matrix[self.Param2Idx.YDD.value, self.Param2Idx.YD.value] = -self.RAMP_UP_1_A1
        else:
            transf_matrix[self.Param2Idx.Y.value, self.Param2Idx.Y.value] = 1
            transf_matrix[self.Param2Idx.Y.value, self.Param2Idx.YD.value] = self.delta_t
            transf_matrix[self.Param2Idx.YDD.value, self.Param2Idx.Y.value] = -self.RAMP_UP_1_A0
            transf_matrix[self.Param2Idx.YDD.value, self.Param2Idx.YD.value] = -self.RAMP_UP_1_A1 - self.RAMP_UP_1_A0 * self.delta_t
        transf_matrix[self.Param2Idx.YDD.value, self.Param2Idx.YDD.value] = -self.RAMP_UP_1_A1 * self.delta_t
        transf_matrix[self.Param2Idx.YDD.value, self.Param2Idx.CONST.value] = (
            self.RAMP_UP_1_B1 * (self.target - self.u_log[-1]) / self.delta_t + self.RAMP_UP_1_B0 * self.target
            )
        transf_matrix[self.Param2Idx.TEMPERATURE.value, self.Param2Idx.TEMPERATURE_D.value] = self.delta_t
        if self.temperature < self.maxTemperature:
            transf_matrix[self.Param2Idx.TEMPERATURE_D.value, self.Param2Idx.TEMPERATURE_D.value] =  0
            transf_matrix[self.Param2Idx.TEMPERATURE_D.value, self.Param2Idx.CONST.value] =  self.maxTemperature * self.T_TEMPER_RAMP_UP_1_SCALER
        else:
            transf_matrix[self.Param2Idx.TEMPERATURE_D.value, self.Param2Idx.TEMPERATURE.value] =  -1
            transf_matrix[self.Param2Idx.TEMPERATURE_D.value, self.Param2Idx.TEMPERATURE_D.value] =  -self.delta_t
            transf_matrix[self.Param2Idx.TEMPERATURE_D.value, self.Param2Idx.CONST.value] =  self.maxTemperature
            transf_matrix[self.Param2Idx.TEMPERATURE_D.value] *= self.T_TEMPER_RAMP_UP_1_SCALER
        if np.dot(transf_matrix[self.Param2Idx.Y.value], self.vector) >= self.RAMP_UP_DYNAMIC_CHANGE_BORDER * self.target:
                self.state = self.States.RAMP_UP_2
                transf_matrix[self.Param2Idx.TEMPERATURE_WHEN_RAMPUP2_STARTS.value, self.Param2Idx.TEMPERATURE_WHEN_RAMPUP2_STARTS.value] = 0
                transf_matrix[self.Param2Idx.TEMPERATURE_WHEN_RAMPUP2_STARTS.value, self.Param2Idx.TEMPERATURE.value] = 1
        self.u_log.append(self.target)

    def __ramp_up_2_handler(self,transf_matrix: np.ndarray,  U: float):
        transf_matrix[self.Param2Idx.YDD.value, self.Param2Idx.YDD.value] = 0
        transf_matrix[self.Param2Idx.Y.value, self.Param2Idx.YD.value] = self.delta_t
        transf_matrix[self.Param2Idx.YD.value, self.Param2Idx.Y.value] = -1
        transf_matrix[self.Param2Idx.YD.value, self.Param2Idx.YD.value] = -self.delta_t
        transf_matrix[self.Param2Idx.YD.value, self.Param2Idx.CONST.value] = self.CTR_COEF * self.target
        transf_matrix[self.Param2Idx.YD.value] *= self.T_RAMP_UP_2_SCALER
        transf_matrix[self.Param2Idx.TEMPERATURE.value, self.Param2Idx.TEMPERATURE.value] = 1
        transf_matrix[self.Param2Idx.TEMPERATURE.value, self.Param2Idx.TEMPERATURE_D.value] = self.delta_t
        if self.temperature < self.maxTemperature:
            transf_matrix[self.Param2Idx.TEMPERATURE_D.value, self.Param2Idx.CONST.value] =  self.maxTemperature * self.T_TEMPER_RAMP_UP_2_SCALER
        else:
            transf_matrix[self.Param2Idx.TEMPERATURE_D.value, self.Param2Idx.TEMPERATURE.value] = - 1
            transf_matrix[self.Param2Idx.TEMPERATURE_D.value, self.Param2Idx.TEMPERATURE_D.value] = -self.delta_t
            transf_matrix[self.Param2Idx.TEMPERATURE_D.value, self.Param2Idx.CONST.value] =  self.maxTemperature
            transf_matrix[self.Param2Idx.TEMPERATURE_D.value] *= self.T_TEMPER_RAMP_UP_2_SCALER
        if np.dot(transf_matrix[self.Param2Idx.Y.value], self.vector) >= self.target:
            self.state = self.States.STEADY
        self.u_log.append(self.target)

    def __steady_handler(self,transf_matrix: np.ndarray,  U: float):
        self.target = U
        transf_matrix[self.Param2Idx.Y.value, self.Param2Idx.YD.value] = self.delta_t
        transf_matrix[self.Param2Idx.YD.value, self.Param2Idx.YD.value] = -self.delta_t * self.STEADY_REACT_SPEED
        transf_matrix[self.Param2Idx.YD.value, self.Param2Idx.Y.value] = - self.STEADY_REACT_SPEED
        transf_matrix[self.Param2Idx.YD.value, self.Param2Idx.CONST.value] = self.target * self.STEADY_REACT_SPEED
        transf_matrix[self.Param2Idx.TEMPERATURE.value, self.Param2Idx.TEMPERATURE.value] = 1
        transf_matrix[self.Param2Idx.TEMPERATURE.value, self.Param2Idx.TEMPERATURE_D.value] = self.delta_t
        if self.temperature < self.maxTemperature:
            transf_matrix[self.Param2Idx.TEMPERATURE_D.value, self.Param2Idx.CONST.value] = self.maxTemperature * self.T_TEMPER_STEADY_LOW_SCALER
        else:
            transf_matrix[self.Param2Idx.TEMPERATURE_D.value, self.Param2Idx.TEMPERATURE.value] = - self.T_TEMPER_STEADY_HIGH_SCALER
            transf_matrix[self.Param2Idx.TEMPERATURE_D.value, self.Param2Idx.TEMPERATURE_D.value] = -self.delta_t * self.T_TEMPER_STEADY_HIGH_SCALER
            transf_matrix[self.Param2Idx.TEMPERATURE_D.value, self.Param2Idx.CONST.value] = self.maxTemperature * self.T_TEMPER_STEADY_HIGH_SCALER
        if self.target == 0:
            self.state = self.States.RAMP_DOWN_1
            transf_matrix[self.Param2Idx.Y_MAX.value, self.Param2Idx.Y_MAX.value] = 0
            transf_matrix[self.Param2Idx.Y_MAX.value, self.Param2Idx.Y.value] = 1
            transf_matrix[self.Param2Idx.TOTAL_RUN_OUT_NEW.value][self.Param2Idx.TOTAL_RUN_OUT_NEW.value] = 1
            transf_matrix[self.Param2Idx.TOTAL_RUN_OUT_NEW.value][self.Param2Idx.CONST.value] = self.run_out_of_switchOff_new
            transf_matrix[self.Param2Idx.SWITCH_NUM.value][self.Param2Idx.SWITCH_NUM.value] = 1
            transf_matrix[self.Param2Idx.SWITCH_NUM.value][self.Param2Idx.CONST.value] = 1
        self.u_log.append(self.target)

    def __ramp_down_1_handler(self,transf_matrix: np.ndarray,  U: float):
        transf_matrix[self.Param2Idx.YD.value, self.Param2Idx.YD.value] = 0
        transf_matrix[self.Param2Idx.YD.value, self.Param2Idx.CONST.value] = - self.vector[self.Param2Idx.Y_MAX.value, 0] * self.T_RAMP_DOWN_1_SCALER
        transf_matrix[self.Param2Idx.Y.value, self.Param2Idx.CONST.value] = - self.delta_t * self.vector[self.Param2Idx.Y_MAX.value] * self.T_RAMP_DOWN_1_SCALER
        transf_matrix[self.Param2Idx.TEMPERATURE.value, self.Param2Idx.TEMPERATURE_D.value] = self.delta_t
        transf_matrix[self.Param2Idx.TEMPERATURE_D.value, self.Param2Idx.TEMPERATURE_D.value] = 0
        transf_matrix[self.Param2Idx.TEMPERATURE_D.value, self.Param2Idx.CONST.value] = - self.RAMP_DOWN_A_SCALER * self.T_TEMPER_RAMP_DOWN_1_SCALER
        if self.production_rate <= self.RAMP_DOWN_DYNAMIC_CHANGE_BORDER:
            self.state = self.States.RAMP_DOWN_2
        self.u_log.append(0)

    def __ramp_down_2_handler(self,transf_matrix: np.ndarray,  U: float):
        transf_matrix[self.Param2Idx.YD.value, self.Param2Idx.YD.value] = 0
        transf_matrix[self.Param2Idx.YD.value, self.Param2Idx.CONST.value] = - self.vector[self.Param2Idx.Y_MAX.value] * self.T_RAMP_DOWN_2_SCALER
        transf_matrix[self.Param2Idx.Y.value, self.Param2Idx.CONST.value] = - self.delta_t * self.vector[self.Param2Idx.Y_MAX.value] * self.T_RAMP_DOWN_2_SCALER
        transf_matrix[self.Param2Idx.TEMPERATURE.value, self.Param2Idx.TEMPERATURE_D.value] = self.delta_t
        transf_matrix[self.Param2Idx.TEMPERATURE_D.value, self.Param2Idx.TEMPERATURE_D.value] = 0
        transf_matrix[self.Param2Idx.TEMPERATURE_D.value, self.Param2Idx.CONST.value] = - self.RAMP_DOWN_A_SCALER * self.T_TEMPER_RAMP_DOWN_2_SCALER
        if self.production_rate <= self.RAMP_DOWN_FINISH_BORDER:
            self.state = self.States.IDLE
        self.u_log.append(0)

    def __incorrect_handler(self,transf_matrix: np.ndarray,  U: float):
        assert False, f"Simulation came up with the incorrect_handler."

    @property
    def dynamics(self):
        return self.vector[[self.Param2Idx.Y.value, self.Param2Idx.YD.value, self.Param2Idx.YDD.value]]

    @property
    def production_rate(self):
        return self.vector[self.Param2Idx.Y.value, 0]

    @property
    def ran_out(self):
        return self.vector[self.Param2Idx.TOTAL_RUN_OUT_NEW.value, 0]

    @property
    def switch_num(self):
        return self.vector[self.Param2Idx.SWITCH_NUM.value, 0]

    @property
    def temperature(self):
        return self.vector[self.Param2Idx.TEMPERATURE.value, 0]

    @property
    def temperature_dynamics(self):
        return self.vector[[self.Param2Idx.TEMPERATURE.value, self.Param2Idx.TEMPERATURE_D.value]]

    @property
    def time(self):
        return self.vector[self.Param2Idx.TIME.value, 0]

    @property
    def hydration_start(self):
        return self.vector[self.Param2Idx.HYDRATION_START.value, 0]
