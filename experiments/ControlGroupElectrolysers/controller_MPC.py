
import numpy as np
import copy
from joblib import Parallel, delayed
from es import *
from control_assessment_model import ControlAssessment
from plant_model import GroupOfElectrolysers


class MPC:
    def __init__(self, planing_horizon, sampling_time_control, sampling_time_plant, sampling_time_plan):
        self.__sampling_time_plant = sampling_time_plant
        self.__sampling_time_plan = sampling_time_plan
        self.__sampling_time_control = sampling_time_control
        self.__control_strategy = None
        assert (self.__sampling_time_control >= self.__sampling_time_plan) and (self.__sampling_time_control % self.__sampling_time_plan == 0), f"The sampling_time_control mast be multiple of the sampling_time_plan!"

    @property
    def control_strategy(self):
        return self.__control_strategy

    def maximiser_ES(self, evolution_strategy, functional, problem_dimension, generations_num, parallel=True, n_jobs=-1):
        es = evolution_strategy
        for i in range(generations_num):
            solutions = es.ask()
            if parallel:
                reward_list = Parallel(n_jobs=n_jobs)(delayed(functional)(solution) for solution in solutions)
            else:
                reward_list = []
                solut_number = 0
                for solution in solutions:  # можно параллельно
                    score = functional(solution)
                    reward_list.append(score)
                    print(str(solut_number) + ' solution is aplied, score = ' + str(score) + '  min-max = ' + str(
                        min(solution)) + ' -- ' + str(max(solution)))
                    # if score > best_score_solution[0]:
                    #     best_score_solution[0] = copy.deepcopy(score)
                    #     best_score_solution[1] = copy.deepcopy(solution)
                    #
                    # if score < worst_score_solution[0]:
                    #     worst_score_solution[0] = copy.deepcopy(score)
                    #     worst_score_solution[1] = copy.deepcopy(solution)
                    solut_number += 1
            es.tell(reward_list)
            es_solution = es.result()
            #         model_params = es_solution[0] # best historical solution
            best_reward = es_solution[1]  # best reward
            curr_best_reward = es_solution[2]  # best of the current batch
            curr_best_reward_my_for_validation = max(reward_list)
            print(f"{i} ==>> {curr_best_reward_my_for_validation} === {curr_best_reward} === {best_reward} === {es.rms_stdev()}")
            if curr_best_reward >= 0:
                break
            # assert curr_best_reward < 0, f"Optimization failed!"
        return [es.result(), es.current_param()]  # best historical solution

    def preprocess_control(self, control):
        ne = len(control)
        U = []
        for j in range(ne):
            if control[j] < 0:
                U.append(0)
            else:
                ctr = min(1, control[j])
                U.append(0.6 + 0.4 * ctr)
        return np.array(U)

    def form_control_strategy_for_plan(self,
                                       instant: int,
                                       plant_model_copy: GroupOfElectrolysers,
                                       plan: np.ndarray,
                                       control_signal_dimension: int) -> None:
        '''
        plant_state is the plant state at current instant
        plan = [plan_(instant), plan_(instant+1) ... plan_(instant+H-1)]
        return of this function is the control strategy over the plan
        '''
        planing_horizon = len(plan)
        control_strategy_length = int(planing_horizon * self.__sampling_time_plan / self.__sampling_time_control)
        problem_dimension = control_signal_dimension * control_strategy_length
        generations_num = 500
        assessment = ControlAssessment(self.__sampling_time_plant, plant_model_copy.electrolyser_max_power)
        def functional(x):
            control_strategy = np.reshape(x, (control_strategy_length, control_signal_dimension))
            plant_model = copy.deepcopy(plant_model_copy)
            trajectory = []
            trajectory_reference = []
            for k in range(int(control_strategy_length * self.__sampling_time_control / self.__sampling_time_plant)):
                ## snap current state of the control system
                plant_state = plant_model.group_state
                [group_output,
                 set_points,
                 outputs,
                 output_derives,
                 temperatures,
                 stack_states,
                 group_deterioration] = plant_state
                ref_out = plan[int(k * self.__sampling_time_plant / self.__sampling_time_plan)]
                control = self.preprocess_control(control_strategy[int(k * self.__sampling_time_plant / self.__sampling_time_control)])
                ## log simulation data
                if k > 0: # ignore init state of the plant
                    trajectory_reference.append(ref_out)
                    trajectory.append(group_output)
                ## make step of dynamics
                plant_model.make_dynamical_step(control)
            Cost_episode = assessment.cost(np.array(trajectory_reference),
                                           np.array(trajectory),
                                           np.array(group_deterioration),
                                           control_strategy)
            return -Cost_episode
        sigma_init = 0.9
        popsize = 50
        # evolution_strategy = PEPG(num_params=problem_dimension,  # number of model parameters
        #                           sigma_init=sigma_init,  # initial standard deviation
        #                           learning_rate=0.1,  # learning rate for standard deviation
        #                           learning_rate_decay=1.0,  # don't anneal the learning rate
        #                           popsize=popsize,  # population size
        #                           average_baseline=False,  # set baseline to average of batch
        #                           weight_decay=0.00,  # weight decay coefficient
        #                           rank_fitness=False,  # use rank rather than fitness numbers
        #                           forget_best=False)  # don't keep the historical best solution)
        evolution_strategy = CMAES(num_params=problem_dimension, sigma_init=sigma_init, popsize=popsize)
        results = self.maximiser_ES(evolution_strategy, functional, problem_dimension, generations_num)
        curr_solution = results[1]
        best_solution = results[0][0]
        best_reward = results[0][1]
        self.__control_strategy = np.reshape(best_solution, (control_strategy_length, control_signal_dimension))




