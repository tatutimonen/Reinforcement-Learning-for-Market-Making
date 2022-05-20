from cProfile import label
import pickle
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from utils.mc_model.plotting import heatmap_Q, show_Q
from environments.mc_model.mc_environment import *
from collections import defaultdict, OrderedDict
import os
import random
import time as t
from datetime import timedelta


def tabular_Q_learning(env, n=1e4, alpha_start=0.1, alpha_end=0.00005,
                       epsilon_start=1, epsilon_end=0.05, epsilon_cutoff=0.25,
                       beta_start=1, beta_end=0.01, beta_cutoff=0.5,
                       gamma=1, exploring_starts=True):
    """
    tabular_Q_learning is a function that performs tabular Q-learning.

    Parameters
    ----------
    env : object from Class SimpleEnv
        environment simulating the Simple Probabilistic Model
    n : int
        the number of episodes to run Q-learning
    alpha_start : float (0<x≤1)
        the value at which alpha starts
    alpha_end : float (0<x≤1)
        the value at which alpha ends
    epsilon_start : float (0<x≤1)
        the value at which epsilon starts
    epsilon_end : float (0<x≤1)
        the value at which epsilon ends
    epsilon_cutoff : float (0<x≤1)
        the proportion of the total number of episodes at which the epsilon_end is reached
    beta_start : float (0<x≤1)
        the value at which beta starts
    beta_end : float (0<x≤1)
        the value at which beta ends
    beta_cutoff : float (0<x≤1)
        the proportion of the total number of episodes at which the beta_end is reached
    gamma : float (0<gamma≤1)
        the discount factor in Q-learning
    exploring_starts : bool
        boolean indicating whether to use exploring starts (True) or not (False)

    Returns
    -------
    Q_tab : defaultdict 
        with all Q-values from the Q-learning
    rewards : list
        list with all episode rewards during training
    Q_zero_average : list
        list with average state-values at (0,0)
    x_values : list
        list with episode indeces used for plotting
    """

    Q_tab = defaultdict(lambda: np.zeros(env._get_action_space_shape()))

    state_action_count = defaultdict(lambda: np.zeros(env._get_action_space_shape()))

    rewards_average = []  # to save the rewards

    Q_zero_average = []

    x_values = []

    reward_grouped = []
    Q_zero_grouped = []

    decreasing_factor = (alpha_end / alpha_start) ** (1 / n)

    alpha = alpha_start

    # n_rewards = 0
    # n_nonzero_rewards = 0

    # ----- SIMULATING -----

    start_time = t.time()

    for episode in range(int(n)):

        # epsilon greedy policy
        epsilon = linear_decreasing(episode, n, epsilon_start, epsilon_end, epsilon_cutoff)

        # update learning rate
        # alpha = linear_decreasing(episode, n, alpha_start, alpha_end, alpha_cutoff)
        alpha = exponential_decreasing(alpha, factor=decreasing_factor)

        # update exploring starts
        beta = linear_decreasing(episode, n, beta_start, beta_end, beta_cutoff)

        # Exploring starts
        if exploring_starts is True:
            if random.random() < beta:
                env.Q_0 = env.observation_space.sample()[0]  # Sample Q_t from the observation space
            else:
                env.Q_0 = 0
        else:
            env.Q_0 = 0

        # Reset the environment
        env.reset()
        episode_reward = 0

        while env.t < env.T:  # As long as the episode isn't over
            # ===== DEBUGGING STATE SPACE =====
            # print("inventory:", env.Q_t)
            # print("inventory level:", env.state()[0])
            # print("="*20)

            state = env.state()

            explore = random.random() < epsilon

            if state not in list(Q_tab.keys()) or explore:  # Random if explore or unvisisted
                action = env.action_space.sample()
            else:  # Maximum otherwise
                action = tuple_action_to_dict(np.unravel_index(Q_tab[state].argmax(), Q_tab[state].shape))

            # TODO: tuple_action_to_dict function
            new_state, action_reward = env.step(action)  # Get the new state and the reward

            action = dict_action_to_tuple(action)

            episode_reward += action_reward  # * (gamma ** env.t)  # Discounting with gamma
            
            # ===== SPARSITY OF REWARDS =====
            # n_rewards += 1
            # n_nonzero_rewards += action_reward != 0

            # ===== DEBUGGING REWARDS =====
            # print("V_t-1:", env.X_t_previous + env.H_t_previous)
            # print("V_t:", env.X_t + env.H_t)
            # print("R_t:", action_reward)
            # print("="*20)

            state_action_count[state][action] += 1

            # Update the Q table
            Q_tab[state][action] = Q_tab[state][action] + alpha * (
                    action_reward + gamma * (np.max(Q_tab[new_state]) - Q_tab[state][action]))

        # Save the reward
        reward_grouped.append(episode_reward)

        # Save the best Q-value
        Q_zero_grouped.append(np.max(Q_tab[(0, 1)]))

        # Printing every 1% of total episodes
        if (episode + 1) % (0.01 * n) == 0:
            percentage = "{:.0%}".format(episode / n)

            time_remaining = str(timedelta(seconds=round((t.time() - start_time) / (episode + 1) * (n - episode - 1), 2)))

            print("\tEpisode", episode + 1, "(" + percentage + "),", time_remaining, "remaining of this run")

        if episode % (max(n / 1e4, 5)) == 0 or episode == n - 1:
            rewards_average.append(np.mean(reward_grouped))

            Q_zero_average.append(np.mean(Q_zero_grouped))

            x_values.append(episode)

            reward_grouped = []
            Q_zero_grouped = []

    # print("\t\tThe discounted average reward over all episodes is:", np.mean(rewards_average))

    # print("\t\t", n_nonzero_rewards, "of the total", n_rewards, "were non-zero")

    return Q_tab, rewards_average, Q_zero_average, x_values


def dict_action_to_tuple(dict):
    """
    translates an action in dict-form to tuple-form

    Parameters
    ----------
    dict : dict
        an action in dict-form

    Returns
    -------
    action : tuple
        an action in tuple-form
    """

    return tuple(np.append(dict["depths"] - 1, dict["market order"]))  # -1 to make it start from zero


def tuple_action_to_dict(tuple):
    """
    translates an action in tuple-form to dict-form

    Parameters
    ----------
    action : tuple
        an action in tuple-form

    Returns
    -------
    dict : dict
        an action in dict-form
    """

    return OrderedDict({"depths": np.array([tuple[0] + 1, tuple[1] + 1]), "market order": tuple[2]})


def exponential_decreasing(value, factor=0.9999):
    """
    returns the value for the next time step

    Parameters
    ----------
    value : float
        the current value
    factor : float
        the factor the value decreases with (<1)

    Returns
    -------
    value : float
        the next value
    """

    return value * factor


def linear_decreasing(episode, n, start, end, cutoff):
    """
    save_Q saves the Q table to a pkl file

    Parameters
    ----------
    episode : int
        the current episode number
    n : int
        the total number of episodes the training will be run for
    tart : float (0<x≤1)
        the value at which the value starts
    end : float (0<x≤1)
        the value at which the value ends
    cutoff : float (0<x≤1)
        the proportion of the total number of episodes at which the end is reached

    Returns
    -------
    value : float
        the current value of the parameter entered
    """

    if episode < cutoff * n:
        value = start + (end - start) * episode / (cutoff * n)
    else:
        value = end

    return value


def save_Q(Q, args, n, rewards_average, Q_zero_average, x_values, suffix="", folder_mode = False, folder_name = None):
    """
    save_Q saves the Q table to a pkl file

    Parameters
    ----------
    Q : dict
        a defaultdictionary will all Q tables. the keys are actions and the values are the actual Q tables
    args : dict
        a dict with parameters used for the environment
    rewards_average : list
        a list with rewards received during training
    Q_zero_average : list
        list with average state-values at (0,0)
    x_values : list
        list with episode indeces used for plotting
    suffix : str
        string put at the end of file names
    folder_mode : bool
        whether or not things should be loaded/saved to files
    folder_name : str
        where files are saved

    Returns
    -------
    file_name : str
        where the file is saved
    """

    # Create the file
    if folder_mode:

        try:
            os.makedirs("results/mc_model/" + folder_name)
        except:
            print("THE FOLDER", folder_name, "ALREADY EXISTS")

        file_name = "results/mc_model/" + folder_name + "/" + fetch_table_name(args, n, suffix) + ".pkl"

    else:
        file_name = "results/mc_model/q_tables/" + fetch_table_name(args, n, suffix) + ".pkl"

    file = open(file_name, "wb")

    # Save the values in the file
    pickle.dump([dict(Q), args, n, rewards_average, Q_zero_average, x_values], file)
    file.close()

    return file_name


def load_Q(filename, default=True, folder_mode = False, folder_name = None):
    """
    loads a Q table from a pkl file

    Parameters
    ----------
    filename : str
        a string for the filename
    default : bool
        if a defaultdictionary or a dictionary should be returned
    folder_mode : bool
        whether or not things should be loaded/saved to files
    folder_name : str
        where files are saved

    Returns
    -------
    Q : dict
        a defaultdictionary/dictionary will all Q tables. the keys are actions and the values are the actual Q tables
    args : dict
        a dict with parameters used for the environment
    rewards_average : list
        a list with rewards received during training
    Q_zero_average : list
        list with average state-values at (0,0)
    x_values : list
        list with episode indeces used for plotting
    """

    if folder_mode:
        results_folder = folder_name

    else:
        results_folder = "q_tables"

    # Load the file
    try:
        file = open("results/mc_model/" + results_folder + "/" + filename + ".pkl", "rb")
    except:
        file = open(filename, "rb")

    Q_raw, args, n, rewards_average, Q_zero_average, x_values = pickle.load(file)

    # If we don't want a defaultdict, just return a dict
    if not default:
        return Q_raw

    # Find d
    dim = Q_raw[(0, 1)].shape[0]

    # Transform to a default_dict
    Q_loaded = defaultdict(lambda: np.zeros((dim, dim)))
    Q_loaded.update(Q_raw)

    return Q_loaded, args, n, rewards_average, Q_zero_average, x_values


def fetch_table_name(args, n, suffix=""):
    """
    creates a filename based on the input arguments

    Parameters
    ----------
    args : dict
        a dictionary with all parameters of the model
    n : int
        how many episodes the Q-learning is run for
    suffix : str
        string put at the end of file names

    Returns
    -------
    table_name : str
        a string including all parameters and their values
    """

    # Creates the table names based on the chosen parameters
    return "Q_" + "_".join(
        [list(args.keys())[i] + str(list(args.values())[i]) for i in range(len(args.values()))]) + "_n" + str(
        int(n)) + "_" + str(suffix)


def plot_rewards(average_rewards, x_values):
    """
    plots the reward

    Parameters
    ----------
    average_rewards : np.array
        an array of the rewards
    x_values : list
        list with episode indeces used for plotting

    Returns
    -------
    None
    """

    plt.figure()
    plt.plot(x_values, average_rewards, label="reward")
    plt.ylabel("Reward")
    plt.xlabel("episode")
    plt.title("Rewards during training")
    plt.legend()
    plt.show()


def plot_Q_zero(Q_zero, x_values):
    """
    plots Q[(0,0)] over time

    Parameters
    ----------
    Q_zero : np.array
        an array of the Q[(0,0)] values
    x_values : list
        list with episode indeces used for plotting

    Returns
    -------
    None
    """

    plt.figure()
    plt.plot(x_values, Q_zero, label="Q[(0,0)]")
    plt.ylabel("reward of best action")
    plt.xlabel("episode")
    plt.title("Best Q-value from the start for every epsiode")
    plt.legend()
    plt.show()


def save_parameters(model_parameters, Q_learning_parameters, folder_name):
    """
    save parameters into a file

    Parameters
    ----------
    model_parameters : dict
        a dictionary with parameters used for the environment
    Q_learning_parameters : dict
        a dictionary with parameters used for the Q-learning
    folder_name : str
        where the file is saved

    Returns
    -------
    None
    """

    file_path = "results/mc_model/" + folder_name + "/parameters.txt"

    with open(file_path, "w") as f:

        f.write("MODEL PARAMETERS\n")
        for key in list(model_parameters.keys()):
            f.write(str(key) + " : " + str(model_parameters[key]) + "\n")

        f.write("\nQ-LEARNING PARAMETERS\n")
        for key in list(Q_learning_parameters.keys()):
            f.write(str(key) + " : " + str(Q_learning_parameters[key]) + "\n")


def Q_learning_multiple(args, Q_learning_args, n=1e5, n_runs=5, 
                        folder_mode = True, folder_name = None):
    """
    does several runs of tabular Q learning

    Parameters
    ----------
    args : dictionary
        a dictionary of the parameters used for the environment
    n : int
        the number of episodes used for training per run
    n_runs : int
        the number of times Q-learning is performed
    folder_mode : bool
        whether or not things should be loaded/saved to files
    folder_name : str
        where files are saved

    Returns
    -------
    file_names : list
        a list with the file names of the Q-matrices saved
    """
    
    suffixes = np.arange(n_runs) + 1

    Q_learning_args["n"] = n

    file_names = []

    start_time = t.time()

    for i, suffix in enumerate(suffixes):
        print("RUN", suffix, "IN PROGRESS...")
        start_time_sub = t.time()

        env = MonteCarloEnv(**args)

        Q_tab, rewards_average, Q_zero_average, x_values = tabular_Q_learning(env, **Q_learning_args)

        file_names.append(save_Q(Q_tab, args, n, rewards_average, Q_zero_average, x_values, suffix, folder_mode=folder_mode, folder_name=folder_name))

        # Calculate run time for the single run
        run_time = str(timedelta(seconds=round(t.time() - start_time_sub, 2)))
        print("...FINISHED IN", run_time)

        # Calculate the remaining time
        if suffix < len(suffixes):
            remaining_time = str(timedelta(seconds=round((len(suffixes)-suffix) * (t.time() - start_time_sub), 2)))
            print(remaining_time, "REMAINING OF THE TRAINING")

        print("="*40)

    # Print the total training time for all runs
    total_time = str(timedelta(seconds=round(t.time() - start_time, 2)))
    print("FULL TRAINING COMPLETED IN", total_time)

    if folder_mode:
        save_parameters(args, Q_learning_args, folder_name)

    return file_names


if __name__ == "__main__":

    if False:
        args = {"include_spread_levels": True, "num_levels": 10, "mm_priority": True, "T": 100,
                "num_time_buckets": 5, "num_inv_buckets": 3}

        folder_name = "test_multiple"
        folder_mode = True

        Q_learning_args = {
            "epsilon_start": 1, "epsilon_end": 0.05, "epsilon_cutoff": 0.5,
            "alpha_start": 0.5, "alpha_end": 0.0005,
            "beta_start": 1, "beta_end": 0.02, "beta_cutoff": 0.5
        }

        Q_learning_multiple(args, Q_learning_args, n=1e2, n_runs=2, folder_mode=folder_mode, folder_name=folder_name)

    if False:

        # ----- RUNNING THE Q-LEARNING -----
        # args = {"d": 4, "T": 5, "dp": 0.01, "min_dp": 0, "alpha": 1e-4, "phi": 1e-5, "use_all_times": True,
        #         "breaching_penalty":False, "breach_penalty":0.01, "reward_scale": 1}
        x0 = init_LOB(num_levels=10, init_ask=10001, init_spread=2, init_volume=1)
        args = {"include_spread_levels": True, "num_levels": 10, "mm_priority": True, "T": 1000,
                "num_time_buckets": 5, "num_inv_buckets": 3, "kappa": 6, "MO_action": False,
                "dt": 200}

        n = 1e3
        suffix = "_Q-testing"

        # env = SimpleEnv(**args, printing=False, debug=False, breach_penalty_function = np.abs)
        env = MonteCarloEnv(**args, ob_start=x0, debug=False)

        # Run the Q-learning
        epsilon_start = 1
        epsilon_end = 0.05
        epsilon_cutoff = 0.50

        alpha_start = 0.5
        alpha_end = 0.05

        beta_start = 1
        beta_end = 0.05
        beta_cutoff = 0.5

        Q_tab, rewards_average, Q_zero_average, x_values = tabular_Q_learning(env, n=int(n),
                                                                              alpha_start=alpha_start,
                                                                              alpha_end=alpha_end,
                                                                              epsilon_start=epsilon_start,
                                                                              epsilon_end=epsilon_end,
                                                                              epsilon_cutoff=epsilon_cutoff,
                                                                              beta_start=beta_start, beta_end=beta_end,
                                                                              beta_cutoff=beta_cutoff,
                                                                              exploring_starts=True)

        print("final Q(0,1):", Q_zero_average[-1])
        print("mean reward of last 10%:", np.mean(np.array(rewards_average)[int(len(rewards_average) * 0.9):]))
        # print(Q_tab)

        if True:
            plot_rewards(rewards_average, x_values)
            plot_Q_zero(Q_zero_average, x_values)

            # Save the Q-table
            save_Q(Q_tab, args, n, rewards_average, Q_zero_average, x_values, suffix)

            # Show the results
            Q_loaded = load_Q(fetch_table_name(args, n, suffix))[0]
            show_Q(Q_loaded)
            heatmap_Q(Q_loaded)

