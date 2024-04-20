# -*- coding: utf-8 -*-
"""PA3_SMDP_QL.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1TdMPUF6keNoX3xSoOQ97Rj0aJrubKh8B
"""

# Importing libraries
import pickle
import numpy as np
import matplotlib.pyplot as plt
import tensorflow as tf
import gym
import random

# Creating environment
env = gym.make('Taxi-v3')

num_actions = env.action_space.n
num_states = env.observation_space.n
row = 5
col = 5

# Actions
SOUTH = 0
NORTH = 1
EAST = 2
WEST = 3
PICK = 4
DROP = 5
total_actions = [SOUTH, NORTH, EAST, WEST, PICK, DROP]
primitive_actions= [SOUTH, NORTH, EAST, WEST]
num_pacts = len(primitive_actions)

# Primary Destinations for Pickup and Drop
RED = 0
GREEN = 1
YELLOW = 2
BLUE = 3
IN_TAXI = 4

passenger_locs = [RED, GREEN, YELLOW, BLUE, IN_TAXI]
destinations = [RED, GREEN, YELLOW, BLUE]
destination_coords = [[0,0], [0,4], [4,0], [4,3]]

num_plocs = len(passenger_locs)
num_dlocs = len(destinations)

# cur_state = ((taxi_row * 5 + taxi_col) * 5 + passenger_location) * 4 + destination

# Epsilon-greedy policy for options and actions

def choose_option_eg(qvals, num_options, eps):
    '''
    Choosing the option for the current state
    based on an exploration-exploitation trade-off
    using epsilon-greedy policy
    '''
    if np.random.rand() < eps:
        # Exploration
        option = np.random.choice(num_options)

    else:
        # Exploitation
        option = np.argmax(qvals)

    return option

def choose_action_eg(qvals, num_pacts, eps):
    '''
    Choosing the action for the current state
    based on an exploration-exploitation trade-off
    using epsilon-greedy policy
    '''
    if np.random.rand() < eps:
        # Exploration
        action = np.random.choice(num_pacts)

    else:
        # Exploitation
        action = np.argmax(qvals)

    return action

def check_passenger_in_taxi(ploc):
    '''
    Checking if passenger in taxi
    '''
    if ploc == 4:
        ptaxi = True
    else:
        ptaxi = False
    return ptaxi

# Defining Options

class Option:
    def __init__(self, desgn_loc, null_act):
        self.goal_loc = destination_coords[desgn_loc]
        self.goal_null_act = null_act
        self.qvals = np.zeros((row, col, num_pacts))
        self.sa_freq = np.zeros((row, col, num_pacts))

    def reset(self):
        self.qvals = np.zeros((row, col, num_pacts))
        self.sa_freq = np.zeros((row, col, num_pacts))

    def execute(self, state, ploc, dloc, ptaxi, eps):
        '''
        Choosing primitive action within the option
        and determining option termination

        '''

        dstate = destination_coords[dloc]
        optdone = False

        if state[0] == self.goal_loc[0] and state[1] == self.goal_loc[1]:
            optdone = True

            if not ptaxi:
                pstate = destination_coords[ploc]
                if pstate[0] == state[0] and pstate[1] == state[1]:
                    # Picking up passenger
                    optact = PICK
                else:
                    # Terminating the option requires taxi to stay in same state for stable update
                    optact = self.goal_null_act
            if ptaxi:
                if dstate[0] == state[0] and dstate[1] == state[1]:
                    # Dropping passenger
                    optact = DROP
                else:
                    # Terminating the option requires taxi to stay in same state for stable update
                    optact = self.goal_null_act
        else:
            # Choose next action
            optact = choose_action_eg(self.qvals[state[0], state[1]], num_pacts, eps)


        return optact, optdone

# Learning parameters
num_episodes = 5000
num_runs = 5
gamma = 0.9
alpha = 0.1

# Epsilon greedy
eps_decay = 0.99
eps_start = 0.5
eps_final = 0.01

# Training taxi

run_returns = []
run_qo = []
run_options = []

for run in range(num_runs):
    print(f'Beginning Run {run+1}')

    # Creating Options
    Red = Option(RED, 1)
    Green = Option(GREEN, 1)
    Yellow = Option(YELLOW, 0)
    Blue = Option(BLUE, 0)

    options = [Red, Green, Yellow, Blue]
    option_names = ['Red', 'Green', 'Yellow', 'Blue']
    num_options = len(options)
    q_o = np.zeros((num_plocs*num_dlocs, num_options))

    eps = eps_start

    ep_rew = []

    for ep in range(num_episodes):
        # print(f'\n Episode {ep} begins!\n')
        episode_reward = 0

        # Initial state
        state = env.reset()
        tx, ty, ploc, dloc = list(env.decode(state))
        t_coord = [tx, ty]

        # Checking if passenger is in taxi
        ptaxi = check_passenger_in_taxi(ploc)

        done = False # Episode flag

        while not done:

            # Get option using ep-greedy
            opt_state = num_dlocs*ploc + dloc
            opt_id = choose_option_eg(q_o[opt_state], num_options, eps)

            opt = options[opt_id]
            optdone = False # Option flag

            start_state = state

            reward_bar = 0
            steps = 0

            # Execute option till termination
            while not optdone:
                ptaxi = check_passenger_in_taxi(ploc)

                # Get primitive action, optact and optdone
                optact, optdone = opt.execute([tx, ty], ploc, dloc, ptaxi, eps)

                # Get next state, reward, done(episode), info(term prob, action mask)
                next_state, reward, done, info = env.step(optact)

                tnx, tny, pnloc, dnloc = list(env.decode(next_state))
                tn_coord = [tnx, tny]
                opt_ns = num_dlocs*pnloc + dnloc
                # print([tx,ty], [tnx,tny], reward, optdone, done, ploc, dloc, pnloc, dnloc)
                reward_bar = gamma*reward_bar + reward
                steps += 1
                episode_reward += reward

                # Update primitive actions
                if optact < 4:
                    opt.qvals[tx, ty, optact] = opt.qvals[tx, ty, optact] + alpha * (reward + gamma*np.max(opt.qvals[tnx, tny]) - opt.qvals[tx, ty, optact])
                    opt.sa_freq[tx, ty, optact] += 1

                    if optdone:
                        opt.sa_freq[tnx, tny, optact] += 1


                state = next_state
                tx, ty, ploc, dloc = list(env.decode(state))
                t_coord = [tx, ty]
                opt_state = opt_ns

            tx_, ty_, ploc_, dloc_ = list(env.decode(start_state))
            opt_start_state = num_dlocs*ploc_ + dloc_

            # Update option
            q_o[opt_start_state, opt_id] = q_o[opt_start_state, opt_id] + alpha * ((reward_bar + ((gamma**steps) * np.max(q_o[opt_ns,:]))) - q_o[opt_start_state, opt_id])

        eps = max(eps_final, eps_decay*eps)
        ep_rew.append(episode_reward)
        rew_avg100 = [np.average(ep_rew[i:i+100]) for i in range(len(ep_rew)-100)]

    print(f'Run: {run+1} - Max reward: {max(ep_rew)}')
    run_returns.append(ep_rew)
    run_qo.append(q_o)
    run_options.append([Red, Green, Yellow, Blue])

# Plotting Episodic Returns averaged over 5 runs

returns_mean = np.mean(run_returns, 0)
plt.plot(returns_mean)
plt.xlabel('Episodes')
plt.ylabel('Episodic Returns')
plt.title('SMDP Q-Learning (Episodic Returns averaged over 5 runs)')

print(f'Maximum return over 5 runs {max(returns_mean)}')

# Plotting Episodic Returns averaged over 5 runs - 400th-5000th episode to visualize exact reward values
xvals = range(400, 5000)
plt.plot(xvals, returns_mean[400:5000])
plt.xlabel('Episodes')
plt.ylabel('Episodic Returns')
plt.title(f'SMDP Q-Learning (Episodic Returns averaged over 5 runs)\n400th-5000th episode to visualize exact reward values')

# Averaging returns every 100 episodes (over 5 runs)
return_avg100 = [np.average(returns_mean[i:i+100]) for i in range(len(returns_mean)-100)]

print(f'Maximum return over 5 runs (returns averaged every 100 episodes in each run) {max(return_avg100)}')

# Plotting Episodic Returns averaged over 5 runs - returns in every run averaged every 100 episodes
plt.plot(return_avg100)
plt.xlabel('Episodes')
plt.ylabel('Episodic Returns (averaged every 100 episodes)')
plt.title('SMDP Q-Learning (Episodic Returns averaged over 5 runs)')

# Plotting Episodic Returns averaged over 5 runs - returns in every run averaged every 100 episodes
# From 400th episode to visualize exact reward values
xvals = range(400,4900)
plt.plot(xvals, return_avg100[400:4900])
plt.xlabel('Episodes')
plt.ylabel('Episodic Returns (averaged every 100 episodes)')
plt.title(f'SMDP Q-Learning (Episodic Returns averaged over 5 runs)\nFrom 400th episode to visualize exact reward values')

# Visualize Q values on heatmap

def plotQvals(Q, message = "Q plot"):
    # Visualize Q values across taxi env
    Q = np.flip(Q, 0)
    plt.figure(figsize=(10,10))
    plt.title(message)
    plt.pcolor(Q.max(-1), edgecolors='k', linewidths=2)
    plt.colorbar()
    def x_direct(a):
        if a in [NORTH, SOUTH]:
            return 0
        return 1 if a == EAST else -1
    def y_direct(a):
        if a in [EAST, WEST]:
            return 0
        return 1 if a == NORTH else -1
    policy = Q.argmax(-1)
    policyx = np.vectorize(x_direct)(policy)
    policyy = np.vectorize(y_direct)(policy)
    idx = np.indices(policy.shape)
    plt.quiver(idx[1].ravel()+0.5, idx[0].ravel()+0.5, policyx.ravel(), policyy.ravel(), pivot="middle", color='red')
    plt.show()

# Visualizing Q values of option policies - Red, Green, Yellow, Blue

fig = plt.figure(figsize=(12, 6), dpi=300)
# fig.title('Q value visualization for the Option policies')

f1 = plotQvals(Red.qvals, 'Learnt Policy of Option Red')
f2 = plotQvals(Green.qvals, 'Learnt Policy of Option Green')
f3 = plotQvals(Yellow.qvals, 'Learnt Policy of Option Yellow')
f4 = plotQvals(Blue.qvals, 'Learnt Policy of Option Blue')

# Visualize state-action frequencies on heatmap

def plot_state_visit(state_visits, message = 'Mean Number of State Visits over 5 runs (5000 episodes each)'):
    # Visualize number of times agent visits each state
    state_visits = np.flip(state_visits, 0)
    plt.figure(figsize=(10,10))
    plt.title(message)
    plt.pcolor(state_visits.max(-1), edgecolors='k', linewidths=2, cmap="GnBu")
    plt.colorbar()
    plt.show()

# Visualizing state-action frequencies of option policies - Red, Green, Yellow, Blue

fig = plt.figure(figsize=(12, 6), dpi=300)
# fig.title('Q value visualization for the Option policies')

f1 = plot_state_visit(Red.sa_freq, 'State-Action Frequencies of Learnt Policy of Option Red')
f2 = plot_state_visit(Green.sa_freq, 'State-Action Frequencies of Learnt Policy of Option Green')
f3 = plot_state_visit(Yellow.sa_freq, 'State-Action Frequencies of Learnt Policy of Option Yellow')
f4 = plot_state_visit(Blue.sa_freq, 'State-Action Frequencies of Learnt Policy of Option Blue')