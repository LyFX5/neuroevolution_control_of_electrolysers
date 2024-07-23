

import numpy as np
import matplotlib.pyplot as plt


delta_t = 0.1 #0.01 # time step size (seconds)

t_max = 23*60

time_work = np.linspace(0, t_max, int(t_max//delta_t))

#========================

y_vals = [34] # 0.2
yd_vals = [0]

u_vals = 54.*np.ones_like(time_work)
#u_vals[0] = 0

ctr_coef = 1
T = t_max / ((u_vals[0] - y_vals[0]) / u_vals[0])
print(T)

for i in range(1,len(time_work)):

    y_prev = y_vals[i-1]
    yd_prev = yd_vals[i-1]
    u_cur = u_vals[i-1]
    
    y = y_prev + delta_t * yd_prev
    #yd = -y / T + ctr_coef * u_cur / T
    yd = u_cur / T

    y_vals.append(y)
    yd_vals.append(yd)


for i in range(len(y_vals)):
    y_vals[i] = y_vals[i]

plt.title("Step response y(t)")
plt.plot(time_work, y_vals, label='y')
plt.plot(time_work, u_vals, label='u')
plt.legend()
plt.grid(visible=True)
plt.show()



