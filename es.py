import gym
import random
import torch
import numpy as np
from collections import deque
import matplotlib.pyplot as plt
from collections import namedtuple, deque
import random
import time
import multiprocessing as mp
import threading

import concurrent.futures

from agent import Agent

print("Cores", mp.cpu_count())
#Number of agents working in parallel
num_agents = 20
agents = []
for i in range(num_agents):
    env = gym.make('CartPole-v0')
    env.seed(i)
    agent = Agent(env, state_size=4, action_size=2, seed=i)
    agents.append(agent)

def sample_reward(current_weight, index, seed, gamma, max_t, std):
    #print("Begin")
    np.random.seed(seed)
    weights = current_weight + (std*np.random.randn(agents[index].get_weights_dim())) 
    reward = agents[index].evaluate(weights, gamma, max_t)
    #print("End")
    return {seed : reward}

def update_weights(weights, seeds, alpha, std, rewards):
    scaled_perturbations = []
    for i in seeds:
        np.random.seed(i)
        scaled_perturbations.append(np.multiply(rewards[i], np.random.randn(agents[0].get_weights_dim())))
    scaled_perturbations = (scaled_perturbations - np.mean(scaled_perturbations)) / np.std(scaled_perturbations)
    n = len(scaled_perturbations)
    deltas = alpha / (n * std) * np.sum(scaled_perturbations, axis=0)
    return weights + deltas

def evolution(n_iterations=1000, max_t=2000, alpha = 0.01, gamma=1.0, std=0.1):
    """Deep Q-Learning.
    
    Params
    ======
        n_iterations (int): number of episodes used to train the agent
        max_t (int): maximum number of timesteps per episode
        alpha (float): iteration step 
        gamma (float): discount rate
        population (int): size of population at each iteration
        std (float): standard deviation of additive noise
    """
    pool = mp.Pool(num_agents)
    scores_deque = deque(maxlen=100)
    scores = []
    current_weights = []
    rewards = {}
    previous_reward = 0

    start_time = time.time()

    current_weights = std*np.random.randn(agents[0].get_weights_dim())

    indexes = [i for i in range(num_agents)]

    for i_iteration in range(1, n_iterations+1):

        seeds = [i+i_iteration*num_agents for i in range(num_agents)]

        rewards.clear()
        with concurrent.futures.ThreadPoolExecutor(max_workers=200) as executor:
            futures = list()
            for j in range(num_agents):
                agent, i, seed = agents[j], j, seeds[j]
                futures.append(executor.submit(sample_reward, current_weights, i, seed, gamma, max_t, std))
            for future in futures:
                return_value = future.result()
                rewards.update(return_value)
        
        current_weights = update_weights(current_weights, seeds, alpha, std, rewards)

        current_rewards = []
        current_rewards.append(agents[0].evaluate(current_weights, gamma=1.0))
        current_reward = np.max(current_rewards)
        scores_deque.append(current_reward)
        scores.append(current_reward)
        
        torch.save(agent.state_dict(), 'checkpoint.pth')
        
        if i_iteration % 1 == 0:
            print('Episode {}\tAverage Score: {:.2f}'.format(i_iteration, np.mean(scores_deque)))
        if i_iteration % 100 == 0:
            elapsed_time = time.time() - start_time
            print("Duration: ", elapsed_time)

        if np.mean(scores_deque)>=200.0:
            print('\nEnvironment solved in {:d} iterations!\tAverage Score: {:.2f}'.format(i_iteration-100, np.mean(scores_deque)))
            elapsed_time = time.time() - start_time
            print("Training duration: ", elapsed_time)
            break
    pool.close()
    return scores


scores = evolution()


# plot the scores
fig = plt.figure()
ax = fig.add_subplot(111)
plt.plot(np.arange(len(scores)), scores)
plt.ylabel('Score')
plt.xlabel('Episode #')
plt.savefig('training_result.png')