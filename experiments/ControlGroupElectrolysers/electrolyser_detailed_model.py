


class Electrolyser():
    def __init__(self, ID, delta_t):

        # моделируется интенсивность выработки 0 <= y <= 1, в взаимосвязи с целевой интенсивностью 0 <= target <= 1
        # рабочая мощность равна 2268,4 W * y, когда интенсивность равня 1,
        # мощность тоже максимальна и равна 2268,4 W.

        self.ID = ID

        self.maxPower = 2400

        self.state = 'idle'

        self.states_list = ['idle', 'heating', 'hydration', 'ramp_up_1', 'ramp_up_2', 'steady',
                            'ramp_down_1', 'ramp_down_2', 'offline', 'error']
        self.target = 0

        self.y_max = 0

        self.envTemperature = 21.0
        self.maxTemperature = 54.2
        self.minTemperature = 21.0
        [Temper, dTemper] = [self.envTemperature, 0.]
        self.TemperatureDinamics = [Temper, dTemper]

        #self.Temperature = 0 # на данный момент dT = self.dTemper*dt, а потом останавливается

        self.delta_t = delta_t
        #self.dTemper = 0.2*self.delta_t

        [y, yd, ydd] = [0.,0.,0.]
        self.dinamics = [y, yd, ydd]

        self.u_log = []

        self.Temperature_when_rampup2_starts = 0

        self.hydration_start = 0

        self.cost_of_switchOn = 0.2
        self.cost_of_switchOff = 0.2
        self.cost_of_work_for_a_delta_t = 0.1 # = power_consumption
        self.total_cost_of_work = 0

        """
        Один час работы стоит 1 H
        Включить = выключить стоит 0.683 H
                
        =>
        
        delta_t секунд работы стоит delta_t / 3600 H
        Включить = выключить стоит 0.683 H
        """

        self.total_run_out_new = 0
        self.run_out_in_delta_t_new = self.delta_t / 3600 # H
        self.run_out_of_switchOn_new = 0.683 # H
        self.run_out_of_switchOff_new = 0.683 # H

        self.total_run_out = 0
        self.run_out_in_delta_t = 0.1
        self.run_out_of_switchOn = (15.2 * 3600 / self.delta_t) * self.run_out_in_delta_t
        self.run_out_of_switchOff = (15.2 * 3600 / self.delta_t) * self.run_out_in_delta_t


        # TODO в форматировании не нормирую износ перед подачей в перцептрон.
        #  сейчас значения маленькие и за эпизод сильно не выростут, но по хорошему нужно нормировать

        self.switch_num = 0
        self.allowed_switch_num = 2

        self.time = 0 # время для моделирования   'hydration'

        #print("intit Electrolyser " + str(self.ID))

    def set_init_state(self, init_state):
        [state, envTemperature, total_cost_of_work, total_run_out] = init_state
        self.state = state
        self.envTemperature = envTemperature
        self.total_cost_of_work = total_cost_of_work
        self.total_run_out = total_run_out


    def getID(self):
        return self.ID

    def getCurrentTarget(self):
        return self.target

    def getDinamics(self):
        return self.dinamics

    def updateDinamics(self, newDinamics, newTemperDinamics):
        [y, yd, ydd] = newDinamics
        self.dinamics[0] = y
        self.dinamics[1] = yd
        self.dinamics[2] = ydd

        [Temper, Temper_d] = newTemperDinamics
        self.TemperatureDinamics[0] = Temper
        self.TemperatureDinamics[1] = Temper_d

    def getTemperatureDinamics(self):
        return self.TemperatureDinamics

    def getState(self):
        state_index = self.states_list.index(self.state)
        return state_index
        # return self.state

    def getRunOut(self):
        # return self.total_run_out # заменили, потому что используем новую модель
        return self.total_run_out_new

    def getSwitchNum(self):
        return self.switch_num

    def apply_control_signal_in_moment(self, U): # integration method симулируется self.delta_t секунд

        assert 0.6 <= U <= 1.0 or U == 0.0

        [y_prev, yd_prev, ydd_prev] = self.getDinamics()

        [Temperature_prev, Temperature_d_prev] = self.getTemperatureDinamics()

        # у модели слишком быстрая температура

        if self.state != 'idle':
            self.time += self.delta_t

            self.total_cost_of_work += self.cost_of_work_for_a_delta_t

            self.total_run_out += self.run_out_in_delta_t
            self.total_run_out_new += self.run_out_in_delta_t_new

        ## START DINAMICS
        if self.state == 'idle':
            self.target = U

            ud = 0
            yd = 0
            y = 0
            ydd = 0

            ## Temperature modeling
            # in idle state just cooling

            T_Temper_idle = 14000 # ============================================= FIT
            Temper_ctr_coef = 1

            Temperature = Temperature_prev + self.delta_t * Temperature_d_prev
            Temperature_d = -Temperature / T_Temper_idle + Temper_ctr_coef * self.envTemperature / T_Temper_idle

            if self.target != 0:

                self.time = 0 # включились

                if Temperature < self.minTemperature:
                    self.state = 'heating'
                else:
                    self.state = 'hydration'
                    self.hydration_start = self.time

                self.total_cost_of_work += self.cost_of_switchOn
                self.total_run_out += self.run_out_of_switchOn
                self.total_run_out_new += self.run_out_of_switchOn_new

                self.switch_num += 1

            self.u_log.append(0)

        elif self.state == 'heating':
            ud = 0
            yd = 0
            y = 0
            ydd = 0

            ## Temperature modeling
            # in heating state heating

            T_Temper_heating = 700  # 3726.0 # ============================================= FIT
            Temper_ctr_coef_heating = 1

            Temperature = Temperature_prev + self.delta_t * Temperature_d_prev
            Temperature_d = self.maxTemperature / T_Temper_heating

            if Temperature >= self.minTemperature:
                self.state = 'hydration'
                self.hydration_start = self.time

            self.u_log.append(0)

        elif self.state == 'hydration':
            ud = 0
            yd = 0
            y = 0
            ydd = 0

            ## Temperature modeling
            # in hydration state hydration for 1 minute

            T_Temper_hydration = 3500 # 3726.0
            Temper_ctr_coef_hydration = 1

            Temperature = Temperature_prev + self.delta_t * Temperature_d_prev
            Temperature_d = self.maxTemperature / T_Temper_hydration

            if self.time - self.hydration_start >= 62: # ============================================= FIT
                self.state = 'ramp_up_1'

            self.u_log.append(0)

        elif self.state == 'ramp_up_1':

            u_cur = self.target
            u_prev = self.u_log[-1]
            ud = (u_cur - u_prev) / self.delta_t

            if y_prev == 0:
                y = 0.08*self.target # ============================================= FIT

            else:
                y = y_prev + self.delta_t * yd_prev

            yd = yd_prev + self.delta_t * ydd_prev

            # меньше коэффициенты знаменателя => меньше скорость # ============================================= FIT
            a0 = 0.000225 #0.000004 #0.09 # 0.01 #9 #0.01 #0.25  # 1
            a1 = 0.03 #0.004 #0.6 #0.2 #1  # 2
            b0 = 1*a0 #* 0.25
            b1 = -22*a0 #9 #* 0.25
            # ydd = -a0 * y_prev - a1 * yd_prev + b1 * ud + b0 * u_cur
            ydd = -a0 * y - a1 * yd + b1 * ud + b0 * u_cur

            ## Temperature modeling
            # in ramp_up_1 state

            if Temperature_prev < self.maxTemperature:
                T_Temper_ramp_up_1 = 3500  # T = t_max / ((u_vals[0] - y_vals[0]) / u_vals[0])

                Temperature = Temperature_prev + self.delta_t * Temperature_d_prev
                Temperature_d = self.maxTemperature / T_Temper_ramp_up_1

            else:
                T_Temper_ramp_up_1 = 3500  # 3726.0

                Temperature = Temperature_prev + self.delta_t * Temperature_d_prev
                Temperature_d = -Temperature / T_Temper_ramp_up_1 + self.maxTemperature / T_Temper_ramp_up_1  # 50 / T_Temper_steady


            y_targ_in_ramp_up_1 = self.target * 0.11 # ============================================= FIT

            if y >= y_targ_in_ramp_up_1:
                self.state = 'ramp_up_2'
                self.Temperature_when_rampup2_starts = Temperature

            self.u_log.append(u_cur)

        elif self.state == 'ramp_up_2':

            T_ramp_up_2 = 500 # ============================================= FIT
            # T_ramp_up_2 = f(Temperature) тем больше (то есть процес тем медленнее, чем меньше температура)
            ctr_coef = 1.097 # ============================================= FIT

            #T_ramp_up_2 = -40 * self.Temperature_when_rampup2_starts + 500 + 40 * (self.maxTemperature-14)

            ud = 0
            u_cur = self.target
            #yd = u_cur/T_ramp_up_2
            y = y_prev + self.delta_t * yd_prev
            yd = -y / T_ramp_up_2 + ctr_coef * u_cur / T_ramp_up_2
            ydd = 0

            ## Temperature modeling
            # in ramp_up_2 state

            if Temperature_prev < self.maxTemperature:
                T_Temper_ramp_up_2 = 3500  # 3726.0
                Temper_ctr_coef_ramp_up_2 = 2

                Temperature = Temperature_prev + self.delta_t * Temperature_d_prev
                Temperature_d = self.maxTemperature / T_Temper_ramp_up_2  # температура при рампапах растет неограниченно пока ток не выйдет в steady

            else:
                T_Temper_ramp_up_2 = 3500  # 3726.0

                Temperature = Temperature_prev + self.delta_t * Temperature_d_prev
                Temperature_d = -Temperature / T_Temper_ramp_up_2 + self.maxTemperature / T_Temper_ramp_up_2  # 50 / T_Temper_steady

            if y >= self.target:
                self.state = 'steady'

            self.u_log.append(u_cur)

        elif self.state == 'steady':

            self.target = U
            u_cur = self.target

            T_steady = 55 # ============================================= FIT

            ud = 0
            #yd = -y_prev/T_steady + u_cur/T_steady
            y = y_prev + self.delta_t * yd_prev
            yd = -y / T_steady + u_cur / T_steady
            ydd = 0

            ## Temperature modeling
            # in steady state

            if Temperature_prev < self.maxTemperature:
                T_Temper_steady = 3500
                Temperature = Temperature_prev + self.delta_t * Temperature_d_prev
                Temperature_d = self.maxTemperature / T_Temper_steady  # температура при рампапах растет неограниченно пока ток не выйдет в steady
            else:
                T_Temper_steady = 200
                Temper_ctr_coef_steady = 1 # тут всегда должен быть 1 потому что это steady

                Temperature = Temperature_prev + self.delta_t * Temperature_d_prev
                Temperature_d = -Temperature / T_Temper_steady + Temper_ctr_coef_steady * self.maxTemperature / T_Temper_steady #50 / T_Temper_steady
                # умножаю self.maxTemperature*(y) чтобы температура понижалась при понижении тока (0 <= y <= 1)

            if self.target == 0:
                self.state = 'ramp_down_1'
                self.y_max = y

                self.total_cost_of_work += self.cost_of_switchOff
                self.total_run_out += self.run_out_of_switchOff
                self.total_run_out_new += self.run_out_of_switchOff_new

                self.switch_num += 1

            self.u_log.append(u_cur)

        elif self.state == 'ramp_down_1':

            T_ramp_down_1 = 20 # ============================================= FIT

            ud = 0
            u_cur = 0 # = self.target
            yd = -self.y_max / T_ramp_down_1 + u_cur / T_ramp_down_1
            y = y_prev + self.delta_t * yd
            ydd = 0

            ## Temperature modeling
            # in ramp_down_1 state

            T_Temper_ramp_down_1 = 4000
            Temper_ctr_coef_steady = 1

            Temperature = Temperature_prev + self.delta_t * Temperature_d_prev
            Temperature_d = -500 / T_Temper_ramp_down_1

            if y_prev <= 0.5: # ============================================= FIT
                self.state = 'ramp_down_2'

            self.u_log.append(u_cur)

        elif self.state == 'ramp_down_2':

            T_ramp_down_2 = 30 # ============================================= FIT

            ud = 0
            u_cur = 0 # = self.target
            yd = -self.y_max / T_ramp_down_2 + u_cur / T_ramp_down_2
            y = y_prev + self.delta_t * yd
            ydd = 0

            ## Temperature modeling
            # in ramp_down_2

            T_Temper_ramp_down_2 = 4000
            Temper_ctr_coef_steady = 1

            Temperature = Temperature_prev + self.delta_t * Temperature_d_prev
            Temperature_d = -500 / T_Temper_ramp_down_2

            if y_prev <= 0.1: # ============================================= FIT ?

                self.time = 0 # выключилис

                self.state = 'idle'
                # добавил чтобы значения не спевали сильно понижаться. 31 03
                # ud = 0
                # yd = 0
                # y = 0
                # ydd = 0

            self.u_log.append(u_cur)

        else:
            print("wrong state")

        newDinamics = [y, yd, ydd]

        if not all([abs(item) <= 1.2 for item in newDinamics]):
            print()
            print(self.ID)
            print(self.state)
            print(self.target)
            print(Temperature)
            print(newDinamics)

        assert all([abs(item) <= 1.2 for item in newDinamics])

        newTemperDinamics = [Temperature, Temperature_d]
        self.updateDinamics(newDinamics, newTemperDinamics)



class ElectrolyserInterface:

    def __init__(self, electrolyser_dynamical_model):
        self.dynamical_model = electrolyser_dynamical_model


    def get_power_consumption(self, avg_timeframe: str): # потребляемая мощность (фактически)
        # работает на самом деле не так. потому что в реальности запрос отправляется на реальное устройство, а не к симуляции

        [y, yd, ydd] = self.dynamical_model.getDinamics()

        power_consumption = y * self.dynamical_model.maxPower

        return power_consumption


    def get_target_power_consumption(self): # мощность, которую будет потреблять, когда выйдет на заданное значение
        # если работает в установившемся режиме, то power_consumption == target_power_consumption

        target_power_consumption = self.dynamical_model.getCurrentTarget() * self.dynamical_model.maxPower

        return target_power_consumption


    def is_running(self):

        return (self.dynamical_model.getState() != 'idle') # или (self.dynamical_model.getState() == 'steady')


    def can_start(self):

        return (self.dynamical_model.getState() == 'idle')


    def start(self):

        pass


    def can_stop(self):

        return (self.dynamical_model.getState() == 'steady')


    def stop(self):

        pass


    def can_control_target_power(self):

        return (self.dynamical_model.getState() == 'steady')


    def set_target_power(self, target):

        pass
