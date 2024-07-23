

import numpy as np
from enum import Enum


class InclusionOfComponent(Enum):
    ON = "on"
    OFF = "off"



class EnergySystemDynamicalModel:
    def __init__(self, dynamical_model_time_step):
        self.dynamical_model_time_step = dynamical_model_time_step # sec
        self.P_RS = 0
        self.P_LD = 0
        self.P_MG = 0
        self.P_FC = 0
        self.P_EZ = 0
        self.BS_charge_discharge_power_max = 1700  # W
        self.SOC_BS_min = 0
        self.SOC_BS_max = 100
        self.P_BS = 0
        self.SOC_BS = 0 # %
        self.BS_capacity = 3370 * 3_600_000 # W*esc
        self.BS_efficiency = 1
        # self.H2 = 0
        self.S_RS = InclusionOfComponent.ON
        self.S_LD = InclusionOfComponent.ON
        # self.S_MG_exp = InclusionOfComponent.ON
        self.S_MG_imp = None
        self.S_BS = None
        self.S_FC = None
        self.S_EZ = None
        self.load_is_supported = True
        self.operation_mode: int = 0

    def battery_dynamic_step(self):
        BS_current_charge = self.BS_capacity * self.SOC_BS / 100
        BS_next_available_charge = BS_current_charge - self.P_BS * self.dynamical_model_time_step * self.BS_efficiency
        BS_next_charge = max(self.BS_capacity * self.SOC_BS_min / 100,
                             min(self.BS_capacity * self.SOC_BS_max / 100, BS_next_available_charge))
        self.SOC_BS = (BS_next_charge / self.BS_capacity) * 100

    def internal_dynamic_step(self):
        self.battery_dynamic_step()

    def mode_1(self):
        P_EX = self.P_RS - self.P_LD
        if P_EX < 0:
            self.load_is_supported = False
        else:
            self.P_MG = - P_EX

    def mode_2(self):
        P_EX = self.P_RS - self.P_LD
        pass

    def mode_3(self):
        P_EX = self.P_RS - self.P_LD
        pass

    def mode_4(self):
        P_EX = self.P_RS - self.P_LD
        if P_EX < 0:
            if self.SOC_BS > self.SOC_BS_min:
                self.P_BS = min(self.BS_charge_discharge_power_max, abs(P_EX))
                P_EX_hat = self.P_BS - abs(P_EX)
                if P_EX_hat < 0: # else P_EX_hat == 0
                    self.P_MG = abs(P_EX_hat)
            else:
                self.P_MG = abs(P_EX)
        else:
            if self.SOC_BS < self.SOC_BS_max:
                self.P_BS = - min(self.BS_charge_discharge_power_max, P_EX)
                self.P_MG = - (P_EX - abs(self.P_BS))
            else:
                self.P_MG = - P_EX

    def mode_5(self):
        P_EX = self.P_RS - self.P_LD
        pass

    def mode_6(self):
        P_EX = self.P_RS - self.P_LD
        pass

    def mode_7(self):
        P_EX = self.P_RS - self.P_LD
        pass

    def mode_8(self):
        P_EX = self.P_RS - self.P_LD
        pass

    def mode_9(self):
        P_EX = self.P_RS - self.P_LD
        pass

    def mode_10(self):
        P_EX = self.P_RS - self.P_LD
        pass

    def mode_11(self):
        P_EX = self.P_RS - self.P_LD
        pass

    def mode_12(self):
        P_EX = self.P_RS - self.P_LD
        pass

    def mode_default(self):
        assert False, "Mode is incorrect!"

    def set_appropriate_state(self):
        if self.S_MG_imp == InclusionOfComponent.OFF and \
           self.S_BS == InclusionOfComponent.OFF and \
           self.S_FC == InclusionOfComponent.OFF and \
           self.S_EZ == InclusionOfComponent.OFF:
            self.mode_1()
            self.operation_mode = 1
        elif self.S_MG_imp == InclusionOfComponent.OFF and \
           self.S_BS == InclusionOfComponent.ON and \
           self.S_FC == InclusionOfComponent.OFF and \
           self.S_EZ == InclusionOfComponent.OFF:
            self.mode_2()
            self.operation_mode = 2
        elif self.S_MG_imp == InclusionOfComponent.ON and \
            self.S_BS == InclusionOfComponent.OFF and \
           self.S_FC == InclusionOfComponent.OFF and \
           self.S_EZ == InclusionOfComponent.OFF:
            self.mode_3()
            self.operation_mode = 3
        elif self.S_MG_imp == InclusionOfComponent.ON and \
            self.S_BS == InclusionOfComponent.ON and \
           self.S_FC == InclusionOfComponent.OFF and \
           self.S_EZ == InclusionOfComponent.OFF:
            self.mode_4()
            self.operation_mode = 4
        elif self.S_MG_imp == InclusionOfComponent.OFF and \
            self.S_BS == InclusionOfComponent.OFF and \
           self.S_FC == InclusionOfComponent.ON and \
           self.S_EZ == InclusionOfComponent.OFF:
            self.mode_5()
            self.operation_mode = 5
        elif self.S_MG_imp == InclusionOfComponent.OFF and \
            self.S_BS == InclusionOfComponent.ON and \
           self.S_FC == InclusionOfComponent.ON and \
           self.S_EZ == InclusionOfComponent.OFF:
            self.mode_6()
            self.operation_mode = 6
        elif self.S_MG_imp == InclusionOfComponent.ON and \
            self.S_BS == InclusionOfComponent.OFF and \
           self.S_FC == InclusionOfComponent.ON and \
           self.S_EZ == InclusionOfComponent.OFF:
            self.mode_7()
            self.operation_mode = 7
        elif self.S_MG_imp == InclusionOfComponent.ON and \
            self.S_BS == InclusionOfComponent.ON and \
           self.S_FC == InclusionOfComponent.ON and \
           self.S_EZ == InclusionOfComponent.OFF:
            self.mode_8()
            self.operation_mode = 8
        elif self.S_MG_imp == InclusionOfComponent.OFF and \
            self.S_BS == InclusionOfComponent.OFF and \
           self.S_FC == InclusionOfComponent.OFF and \
           self.S_EZ == InclusionOfComponent.ON:
            self.mode_9()
            self.operation_mode = 9
        elif self.S_MG_imp == InclusionOfComponent.OFF and \
            self.S_BS == InclusionOfComponent.ON and \
           self.S_FC == InclusionOfComponent.OFF and \
           self.S_EZ == InclusionOfComponent.ON:
            self.mode_10()
            self.operation_mode = 10
        elif self.S_MG_imp == InclusionOfComponent.ON and \
            self.S_BS == InclusionOfComponent.OFF and \
           self.S_FC == InclusionOfComponent.OFF and \
           self.S_EZ == InclusionOfComponent.ON:
            self.mode_11()
            self.operation_mode = 11
        elif self.S_MG_imp == InclusionOfComponent.ON and \
            self.S_BS == InclusionOfComponent.ON and \
           self.S_FC == InclusionOfComponent.OFF and \
           self.S_EZ == InclusionOfComponent.ON:
            self.mode_12()
            self.operation_mode = 12
        else:
            self.mode_default()
            self.operation_mode = -1
        self.internal_dynamic_step()

    def set_initial_state(self, initial_state):
        [self.P_RS,
         self.P_LD,
         self.P_FC,
         self.P_EZ,
         self.SOC_BS,
         self.S_MG_imp,
         self.S_FC,
         self.S_EZ,
         self.S_BS] =    initial_state
        self.P_MG = 0
        self.P_BS = 0
        self.load_is_supported = True
        self.set_appropriate_state()

    def process_control_signal(self, control_signal):
        # TODO на самом деле эталонные значения, предлогаемые контроллером, могут и не реализоваться
        [self.S_MG_imp, self.S_BS, self.S_FC, self.S_EZ, self.P_FC, self.P_EZ] = control_signal

    def step(self, disturbance_signal, control_signal):
        self.P_RS, self.P_LD = disturbance_signal
        self.process_control_signal(control_signal)
        self.set_appropriate_state()

    def get_current_state(self):
        return [self.P_RS,
                self.P_LD,
                self.P_MG,
                self.P_FC,
                self.P_EZ,
                self.P_BS,
                self.SOC_BS,
                self.S_MG_imp,
                self.S_BS,
                self.S_FC,
                self.S_EZ,
                self.load_is_supported,
                self.operation_mode]


class Controller:
    def __init__(self, dynamical_model_time_step):
        self.dynamical_model_time_step = dynamical_model_time_step

    def form_control_signal(self, current_state, current_step):
        S_MG_imp_ref = InclusionOfComponent.ON
        S_BS_ref = InclusionOfComponent.ON
        S_FC_ref = InclusionOfComponent.OFF
        S_EZ_ref = InclusionOfComponent.OFF
        P_FC_ref = 0
        P_EZ_ref = 0
        return [S_MG_imp_ref, S_BS_ref, S_FC_ref, S_EZ_ref, P_FC_ref, P_EZ_ref]


class UncontrollableSignalsSource:
    def __init__(self, dynamical_model_time_step):
        self.dynamical_model_time_step = dynamical_model_time_step

    def set_up(self, number_of_simulation_time_steps):
        pass

    def form_disturbance_signal(self, simulation_steps_number, current_step):
        P_LD = 5000
        P_RS = 0
        P_RS_max = 10000
        coef = P_RS_max / (simulation_steps_number * 0.5)
        if simulation_steps_number * 0.1 < current_step < simulation_steps_number * 0.9:
            if current_step < simulation_steps_number * 0.5:
                P_RS = coef * current_step
            else:
                P_RS = coef * (simulation_steps_number - current_step)
            # if (current_step % 50) == 0:
                # P_RS += P_RS * np.random.uniform(0, 0.2)
            P_RS += P_RS * 0.2 * np.sin(current_step / 100)
        return [P_RS, P_LD]


def simulate_energy_system(simulation_steps_number, dynamical_model_time_step, initial_state, disturbance_signal_source, control_signal_source):
    # data logs
    P_RS_data = []
    P_LD_data = []
    P_MG_data = []
    P_FC_data = []
    P_EZ_data = []
    P_BS_data = []
    SOC_BS_data = []
    operation_mode_data = []
    # init set up
    microgrid = EnergySystemDynamicalModel(dynamical_model_time_step)
    microgrid.set_initial_state(initial_state)
    disturbance_signal_source.set_up(simulation_steps_number)
    # simulation loop
    for k in range(simulation_steps_number):
        # get state(k)
        current_state = microgrid.get_current_state()
        # collect data
        [P_RS,
         P_LD,
         P_MG,
         P_FC,
         P_EZ,
         P_BS,
         SOC_BS,
         S_MG_imp,
         S_BS,
         S_FC,
         S_EZ,
         load_is_supported,
         operation_mode] = current_state
        P_RS_data.append(P_RS)
        P_LD_data.append(P_LD)
        P_MG_data.append(P_MG)
        P_FC_data.append(P_FC)
        P_EZ_data.append(P_EZ)
        P_BS_data.append(P_BS)
        SOC_BS_data.append(SOC_BS)
        operation_mode_data.append(operation_mode)
        # get controllable signals reference values
        control_signal = control_signal_source.form_control_signal(current_state, current_step=k)
        # get uncontrollable signals values
        disturbance_signal = disturbance_signal_source.form_disturbance_signal(simulation_steps_number, current_step=k)
        # calculate appropriate state(k+1)
        microgrid.step(disturbance_signal, control_signal)
    return [P_RS_data,
            P_LD_data,
            P_MG_data,
            P_FC_data,
            P_EZ_data,
            P_BS_data,
            SOC_BS_data,
            operation_mode_data]










