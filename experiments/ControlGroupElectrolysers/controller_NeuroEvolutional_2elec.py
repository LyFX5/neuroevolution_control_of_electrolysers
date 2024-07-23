import numpy as np
import copy
import torch
import torch.nn as nn
import torch.optim as optim


class DNetwork(nn.Module):
    def __init__(self, number_of_electrolysers):
        super(DNetwork, self).__init__()
        number_of_the_plant_devices = number_of_electrolysers
        desired_curve_current_step = 1
        desired_curve_next_23_steps = 23
        devices_params = 5 # [El_Targets, El_OutputRate, El_OutputRate_dot, El_RunOuts, EL_num_of_switches]
        States_one_hot_dim = 10 # ['idle', 'heating', 'hydration', 'ramp_up_1', 'ramp_up_2', 'steady', 'ramp_down_1', 'ramp_down_2', 'offline', 'error']
        self.state_dim = desired_curve_current_step + \
                         desired_curve_next_23_steps + \
                         devices_params * number_of_the_plant_devices + \
                         States_one_hot_dim * number_of_the_plant_devices
        self.action_dim = number_of_the_plant_devices
        hiden_layer_len_1 = 500
        hiden_layer_len_2 = 500
        self.hidden_1 = nn.Linear(self.state_dim, hiden_layer_len_1, bias=True)
        self.hidden_2 = nn.Linear(hiden_layer_len_1, hiden_layer_len_2, bias=True)
        self.output = nn.Linear(hiden_layer_len_2, self.action_dim, bias=True)
        self.activation_on_hidden_1 =  nn.Tanh() # nn.ReLU()
        self.activation_on_hidden_2 = nn.Tanh() #
        self.activation_on_output = nn.Tanh()  # nn.Softmax()

    def forward(self, x):
        x = self.hidden_1(x)
        x = self.activation_on_hidden_1(x)
        x = self.hidden_2(x)
        x = self.activation_on_hidden_2(x)
        x = self.output(x)
        #x = self.activation_on_output(x)
        x = self.activation_on_output(x)
        return x


class Agent:
    def __init__(self):
        self.model = DNetwork(2)
        self.model_shapes = []
        orig_model = copy.deepcopy(self.model)
        for param in orig_model.parameters():
            p = param.data.cpu().numpy()
            self.model_shapes.append(p.shape)
        self.criterion = nn.MSELoss()
        self.optimizer = optim.Adam(params=self.model.parameters(), lr=0.02)
        self.sigma = 0.01

    def updateParams(self, flat_param: np.ndarray):
        idx = 0
        i = 0
        for param in self.model.parameters():
            delta = np.product(self.model_shapes[i])
            block = flat_param[idx:idx + delta]
            block = np.reshape(block, self.model_shapes[i])
            i += 1
            idx += delta
            block_data = torch.from_numpy(block).float()
            param.data = block_data

    def getAction(self, state):
        # with torch.no_grad():
        action = self.model(torch.from_numpy(state).float()).detach().numpy()
        # action = norm_sample(action, self.sigma)
        # np.clip(action, -1, 1, out=action)
        return action

    # def fit(self, states, actions):
    #     states = torch.from_numpy(states).float()
    #     actions = torch.from_numpy(actions).float()
    #     #self.model.train()
    #     self.optimizer.zero_grad()
    #     guessies = self.model(states)
    #     loss = self.criterion(guessies, actions)
    #     loss.backward()
    #     self.optimizer.step()
    #     return loss.item()
    
    def formate_state(self, plant_state, plan: np.ndarray) -> np.ndarray:
        [group_output,
         set_points,
         outputs,
         output_derives,
         temperatures,
         stack_states,
         group_deterioration] = plant_state
        number_of_electrolysers = len(set_points)
        x_desired_curve = plan / number_of_electrolysers
        x_El_Targets = np.array(set_points)
        x_El_OutputRate = np.array(outputs)
        x_El_OutputRate_dot = np.array(output_derives)
        max_value_El_Temperatures = 54.2 + 0.2
        x_El_Temperatures = np.array(temperatures) / max_value_El_Temperatures
        x_El_States = np.array(stack_states)
        states_list = ['idle', 'heating', 'hydration', 'ramp_up_1', 'ramp_up_2', 'steady',
                       'ramp_down_1', 'ramp_down_2', 'offline', 'error']
        x_El_States_one_hot = np.zeros((x_El_States.size, len(states_list)))
        x_El_States_one_hot[np.arange(x_El_States.size), x_El_States] = 1
        x_El_States_one_hot = np.reshape(x_El_States_one_hot, (1, len(states_list) * number_of_electrolysers))[0]
        x_El_RunOuts = np.array(group_deterioration)
        El_RunOuts_norm_value = sum(x_El_RunOuts)  # TODO не хорошо нормируется для подачи на НС
        if El_RunOuts_norm_value != 0:
            x_El_RunOuts /= El_RunOuts_norm_value  # нормирую чтобы подать в сеть, но будут учитываться не абсалютные значения
        state = np.concatenate((x_desired_curve,
                                x_El_Targets,
                                x_El_OutputRate,
                                x_El_OutputRate_dot,
                                x_El_Temperatures,
                                x_El_States_one_hot,
                                x_El_RunOuts))
        return state

    def interpret_action(self, action):
        assert all([-1 <= item <= 1 for item in action])
        ne = len(action)
        U = []
        for j in range(ne):
            if action[j] < 0:
                U.append(0)
            else:
                U.append(0.6 + 0.4 * action[j])
        return np.array(U)
