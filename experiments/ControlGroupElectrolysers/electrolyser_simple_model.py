from typing import List

import numpy as np

class LDDS_SISO:
    def __init__(self, A: np.ndarray, B: np.ndarray, C: np.ndarray, sampling_time: float) -> None:
        self.__dt: float = sampling_time
        self.__A: np.ndarray = A
        self.__B: np.ndarray = B
        self.__C: np.ndarray = C
        self.__x: np.ndarray = None
        self.__y: float = None

    def set_initial_state(self, x0: np.ndarray) -> None:
        self.__x = x0
        self.__y = np.matmul(self.__C, self.__x)[0]

    def make_dynamical_step(self, u: float) -> None:
        assert self.__x is not None, f'Set up the initial state first, please!'
        self.__x = np.matmul(self.__A, self.__x) + np.multiply(u, self.__B)
        self.__y = np.matmul(self.__C, self.__x)[0]

    @property
    def x(self):
        return self.__x

    @property
    def y(self):
        return self.__y


class Electrolyser(LDDS_SISO):
    def __init__(self,
                 sampling_time: float = 5,
                 init_output: np.ndarray = np.array([[0], [0]]),
                 init_run_out: float = 0):
        # y(k+2) = a1*y(k+1) + a0*y(k) + b1*u(k+1) + b0*u(k)
        # [1.4669415710603944, -0.478227825846913, -0.0005482814722645168 / 0.961959, 0.011409160041332633 / 0.961959]
        self.__a1 = 1.4669415710603944
        self.__a0 = -0.478227825846913
        self.__b1 = -0.0005482814722645168 / 0.961959
        self.__b0 = 0.011409160041332633 / 0.961959
        self.__d3 = 1 # 0.683
        self.__d4 = 0 # sampling_time / 3600
        self.__init_output = init_output
        super(Electrolyser, self).__init__(A=np.array([[self.__a1, 1], [self.__a0, 0]]),
                                           B=np.array([[self.__b1], [self.__b0]]),
                                           C=np.array([1, 0]),
                                           sampling_time=sampling_time)
        self.set_initial_state(self.__init_output)
        self.y_prev = self.y
        self.__run_out = init_run_out
        self.__EPS = 0.000001

    def make_dynamical_step_with_run_out(self, u: float) -> None:
        if (abs(self.y) <= self.__EPS and u > self.__EPS) or (abs(self.y) <= self.__EPS and self.y_prev > self.__EPS):
            # switch on / off
            self.__run_out += self.__d3
        elif (self.y > self.__EPS) and (u > self.__EPS):
            # steady operating
            self.__run_out += self.__d4
        self.y_prev = self.y
        self.make_dynamical_step(u)

    @property
    def state(self) -> List[float]:
        return [self.y, self.__run_out]


















