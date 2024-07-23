

import cma
import numpy as np

cma = CMAES(num_params, sigma_init=sigma_init, popsize=population)
es = cma

while True:

    solutions = es.ask()

    reward_list = []

    for solution in solutions:
        resalts = Simulation.simulate(solution)
        reward = estimate(resalts)
        reward_list.append(reward)

    es.tell(reward_list)

    es_solution = es.result()

    model_params = es_solution[0] # best historical solution
    reward = es_solution[1] # best reward
    curr_reward = es_solution[2] # best of the current batch
    # model.set_model_params(np.array(model_params).round(4))

    if good:
        break








