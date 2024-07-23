


class Electrolyser():
    def __init__(self, elec_id: int, sampling_time: float, init_deterioration: float = 0) -> None:
        ## configuration fields
        self.__id = elec_id
        self.__maxPower = 2400
        self.__EPS = 0.0001
        self.__electrolyser_stack_state = 0
        ## dynamical fields
        self.__dt = sampling_time
        self.__set_point = 0 # u(k) не влияет на y(k). к чему будет стремиться на следующем шаге
        self.__set_point_prev = 0 # u(k-1). к чему стремится сейчас
        self.__set_point_prev_prev = 0 # u(k-2)
        self.__y = 0 # y(k)
        self.__y_prev = 0 # y(k-1)
        self.__y_prev_prev = 0 # y(k-2)
        self.__steady = False
        self.__steady_prev = False
        self.__y_before_switching_of = 0
        self.__temperature_env = 21.0
        self.__temperature_max = 54.2
        self.__temperature_min = 21.0
        self.__temperature = self.__temperature_env
        self.__temperature_prev = self.__temperature_env
        self.__hydration_time = 0
        self.__hydration_duration = 62
        self.__deterioration = init_deterioration
        self.__deterioration_constant_1 = 0.6
        self.__deterioration_constant_2 = self.__dt / 3600
        ## constraint fialds
        self.__set_point_lower_bound = 0.6
        self.__set_point_upper_bound = 1

    @property
    def output(self) -> float:
        return self.__y

    @property
    def output_prev(self) -> float:
        return self.__y_prev

    @property
    def set_point(self) -> float:
        return self.__set_point

    @property
    def temperature(self) -> float:
        return self.__temperature

    @property
    def electrolyser_stack_state(self) -> int:
        return self.__electrolyser_stack_state

    @property
    def deterioration(self) -> float:
        return self.__deterioration
    
    @property
    def maxPower(self) -> float:
        return self.__maxPower

    def step(self, u: float) -> None:
        assert self.__set_point_lower_bound <= u <= self.__set_point_upper_bound or u == 0.0
        self.__y_prev_prev = self.__y_prev
        self.__y_prev = self.__y
        self.__set_point_prev_prev = self.__set_point_prev
        self.__set_point_prev = self.__set_point
        self.__temperature_prev = self.__temperature
        self.__steady_prev = self.__steady
        if self.__y_prev <= self.__EPS and self.__set_point_prev <= self.__EPS: # idle
            self.__steady = False
            self.__y = 0
            self.__set_point = u
            T_Temper_idle = 14000
            Temper_ctr_coef = 1
            self.__temperature = self.__temperature_prev + self.__dt * (-self.__temperature_prev + Temper_ctr_coef * self.__temperature_env) / T_Temper_idle
            self.__hydration_time = 0
            self.__electrolyser_stack_state = 0
        elif self.__temperature < self.__temperature_min: # heating
            T_Temper_heating = 700
            self.__temperature = self.__temperature_prev + self.__dt * (self.__temperature_max / T_Temper_heating)
            self.__electrolyser_stack_state = 1
        elif self.__hydration_time < self.__hydration_duration: # hydration
            T_Temper_hydration = 3500
            self.__temperature = self.__temperature_prev + self.__dt * (self.__temperature_max / T_Temper_hydration)
            self.__hydration_time += self.__dt
            self.__electrolyser_stack_state = 2
        elif self.__y_prev <= 0.11 * self.__set_point_prev and not self.__steady and self.__set_point_prev > self.__EPS: # rump-up_1
            a0 = 0.000225
            a1 = 0.03
            b0 = 1 * a0
            b1 = -22 * a0
            h = self.__dt
            a_ru1_1 = h * a1 - 2
            a_ru1_0 = 1 - h * a1 + (h ** 2) * a0
            b_ru1_1 = h * b1
            b_ru1_0 = (h ** 2) * b0 - h * b1
            if self.__y_prev == 0:
                self.__y = 0.08 * self.__set_point_prev
                self.__y_prev = 0.08 * self.__set_point_prev
                self.__y_prev_prev = 0.08 * self.__set_point_prev
                self.__set_point_prev = 0
            else:
                self.__y = - a_ru1_1 * self.__y_prev - a_ru1_0 * self.__y_prev_prev + b_ru1_1 * self.__set_point_prev + b_ru1_0 * self.__set_point_prev_prev
            self.__electrolyser_stack_state = 3
            T_Temper_ramp_up_1 = 3500
            if self.__temperature_prev < self.__temperature_max:
                self.__temperature = self.__temperature_prev + self.__dt * self.__temperature_max / T_Temper_ramp_up_1
            else:
                self.__temperature = self.__temperature_prev + self.__dt * (-self.__temperature_prev + self.__temperature_max) / T_Temper_ramp_up_1
        elif self.__set_point_prev - self.__y_prev > self.__EPS and not self.__steady and self.__set_point_prev > self.__EPS: # rump-up_2
            T = 500
            a_ru2 = (1 - self.__dt / T)
            b_ru2 = 1.097 * self.__dt / T
            self.__y = a_ru2 * self.__y_prev + b_ru2 * self.__set_point
            self.__electrolyser_stack_state = 4
            T_Temper_ramp_up_2 = 3500
            if self.__temperature_prev < self.__temperature_max:
                self.__temperature = self.__temperature_prev + self.__dt * self.__temperature_max / T_Temper_ramp_up_2
            else:
                self.__temperature = self.__temperature_prev + self.__dt * (-self.__temperature_prev + self.__temperature_max) / T_Temper_ramp_up_2
        elif self.__set_point_prev > self.__EPS and (self.__set_point_prev - self.__y_prev <= self.__EPS or self.__steady): # steady
            self.__steady = True
            T = 55
            a_s = (1 - self.__dt / T)
            b_s = self.__dt / T
            self.__y = a_s * self.__y_prev + b_s * self.__set_point_prev
            self.__set_point = u
            self.__y_before_switching_of = self.__y
            self.__electrolyser_stack_state = 5
            if self.__temperature_prev < self.__temperature_max:
                T_Temper_steady = 3500
                self.__temperature = self.__temperature_prev + self.__dt * self.__temperature_max / T_Temper_steady
            else:
                T_Temper_steady = 200
                self.__temperature = self.__temperature_prev + self.__dt * (-self.__temperature_prev + self.__temperature_max) / T_Temper_steady
        elif self.__y_prev > 0.5: # rump-down_1
            self.__steady = False
            T = 20
            self.__y = self.__y_prev - self.__dt * self.__y_before_switching_of / T
            self.__electrolyser_stack_state = 6
            T_Temper_ramp_down_1 = 4000
            self.__temperature = self.__temperature_prev + self.__dt * (-500 / T_Temper_ramp_down_1)
        else: # rump-down_2
            T = 30
            self.__y = self.__y_prev - self.__dt * self.__y_before_switching_of / T
            self.__electrolyser_stack_state = 7
            T_Temper_ramp_down_2 = 4000
            self.__temperature = self.__temperature_prev + self.__dt * (-500 / T_Temper_ramp_down_2)
        ## deterioration_dynamics_step
        self.deterioration_dynamics_step()

    def deterioration_dynamics_step(self) -> None:
        if self.__steady and (not self.__steady_prev) or (not self.__steady) and self.__steady_prev:
            self.__deterioration += 1. # self.__deterioration_constant_1
        elif self.__electrolyser_stack_state != 0:
            self.__deterioration += 0. # self.__deterioration_constant_2







