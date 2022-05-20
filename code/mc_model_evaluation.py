from mc_model_mm_q_learning import load_Q, show_Q, Q_learning_multiple, tuple_action_to_dict, heatmap_Q, \
    tabular_Q_learning, fetch_table_name, save_Q
from environments.mc_model.mc_environment import *
from utils.mc_model.plotting import heatmap_Q_std, heatmap_Q_n_errors
import numpy as np
import matplotlib.pyplot as plt
from tabulate import tabulate
from collections import defaultdict

import os
os.environ["KMP_DUPLICATE_LIB_OK"]="TRUE"

def evaluate_Q_matrix(matrix_path, n, folder_mode=False, folder_name=None, Q_tab = None, args = None, return_X_Q_V=False):
    """
    returns the rewards for n runs based on a given Q-table

    Parameters
    ----------
    matrix_path : str
        the file path for the Q-table to be evaluated
    n : int
        how many episodes that will be simulated
    folder_mode : bool
        whether or not things should be loaded/saved to files
    folder_name : str
        where files are saved
    Q_tab : object
        a Q-table, if not given, one will be loaded
    args : dict
        a dictionary with arguments used for the environment
    return_X_Q_V : bool
        whether or not cash, inventory and value process should be returned

    Returns
    -------
    rewards : list
        a list of all the simulated rewards
    opt_action : tuple
        the best action at (0,0)
    Q_star : float
        the state-value at (0,0)
    Qs : np.array
        an array with inventory values
    Xs : np.array
        an array with cash values    
    Vs : np.array
        an array with current value of position   
    """

    if Q_tab == None:
        Q_tab, args, _, _, _, _ = load_Q(matrix_path, folder_mode=folder_mode, folder_name=folder_name)

    env = MonteCarloEnv(**args, debug=False)

    Qs = np.zeros((int(n), int(env.T/env.dt)))
    Xs = np.zeros((int(n), int(env.T/env.dt)))
    Vs = np.zeros((int(n), int(env.T/env.dt)))

    rewards = list()

    for episode in range(int(n)):

        env.reset()
        disc_reward = 0

        while env.t < env.T:
            state = env.state()

            action = np.unravel_index(Q_tab[state].argmax(), Q_tab[state].shape)
            
            action = tuple_action_to_dict(action)

            new_state, action_reward = env.step(action)  # Get the new state and the reward

            disc_reward += action_reward  # * (gamma ** env.t)  # Discounting with gamma

            Qs[episode, int(env.t/env.dt - 1)] = env.Q_t
            Xs[episode, int(env.t/env.dt - 1)] = env.X_t
            Vs[episode, int(env.t/env.dt - 1)] = env.H_t + env.X_t

        rewards.append(disc_reward)

    start_state = (0,1)

    opt_action = np.unravel_index(Q_tab[start_state].argmax(), Q_tab[start_state].shape)
    Q_star = Q_tab[start_state][opt_action]

    if return_X_Q_V is False:
        return rewards, opt_action, Q_star
    else:
        return rewards, opt_action, Q_star, Qs, Xs, Vs


def evaluate_constant_strategy(args_environment, n=1000, c=1):
    """
    returns the rewards for n runs based on the constant strategy - c ticks from the mid price

    Parameters
    ----------
    args_environment : dict
        the parameters used for the environment
    n : int
        how many episodes that will be simulated
    c : int
        the number of ticks away from the mid price

    Returns
    -------
    rewards : list
        a list of all the simulated rewards
    """

    env = MonteCarloEnv(**args_environment, debug=False)

    rewards = list()

    for _ in range(int(n)):

        env.reset()
        disc_reward = 0

        while env.t < env.T:
            action = tuple_action_to_dict((c, c, 0))

            _, action_reward = env.step(action)  # Get the new state and the reward

            disc_reward += action_reward # * (gamma ** env.t)  # Discounting with gamma

        rewards.append(disc_reward)

    return rewards


def evaluate_random_strategy(args_environment, n=1000):
    """
    returns the rewards for n runs based on a random strategy

    Parameters
    ----------
    args_environment : dict
        the parameters used for the environment
    n : int
        how many episodes that will be simulated

    Returns
    -------
    rewards : list
        a list of all the simulated rewards
    """

    env = MonteCarloEnv(**args_environment, debug=False)

    rewards = list()

    for _ in range(int(n)):

        env.reset()
        disc_reward = 0

        while env.t < env.T:
            state = env.state()

            action = env.action_space.sample()

            new_state, action_reward = env.step(action)  # Get the new state and the reward

            disc_reward += action_reward # * (gamma ** env.t)  # Discounting with gamma

        rewards.append(disc_reward)

    return rewards


def evaluate_strategies_multiple_Q(file_names, args, mean_rewards, Q_mean, n_test=1e2, c=1, 
                                    folder_mode=False, folder_name=None, save_mode = False):
    """
    compares different strategies with boxplots and a table with mean and rewards

    Parameters
    ----------
    file_names : list
        a list with the paths for the Q-tables
    args : dict
        the parameters used for the environment
    mean_rewards : list
        the mean rewards of the Q-tables tested
    n_test : int
        the number of episodes the strategies are evaluated for
    c : int
        the number of ticks the constant strategies uses
    folder_mode : bool
        whether or not things should be loaded/saved to files
    folder_name : str
        where files are saved
    save_mode : bool
        whether or not table and figures should be saved or displayed

    Returns
    -------
    None
    """

    args_environment = args

    # Get the constant rewards
    # print("\tevaluating constant strategy...", end="")
    rewards_constant = evaluate_constant_strategy(args_environment, n=n_test, c=c)
    print(".", end="")
    # print(" done")

    # Get the random rewards
    # print("\tevaluating random strategy...", end="")
    rewards_random = evaluate_random_strategy(args_environment, n=n_test)
    print(".", end="")
    # print(" done")

    # Get the best Q-learning rewards
    # print("\tevaluating best Q-learning run...", end="")
    best_idx = np.argmax(mean_rewards)
    rewards_Q_learning_best, _, _ = evaluate_Q_matrix(file_names[best_idx], n=n_test, folder_mode=folder_mode, folder_name=folder_name)
    print(".", end="")
    # print(" done")

    # Get the average Q-learning  rewards
    # print("\tevaluating average of Q-learning runs...", end="")
    rewards_Q_learning_average, _, _ = evaluate_Q_matrix(None, n=n_test, folder_mode=folder_mode, folder_name=folder_name, Q_tab=Q_mean, args=args)
    print(".", end="")

    data = [rewards_constant,
            rewards_random,
            rewards_Q_learning_best,
            rewards_Q_learning_average]

    labels = ["constant (d=" + str(c) + ")",
              "random",
              "Q_learning (best run)",
              "Q_learning (average)"]

    headers = ['strategy', 'mean reward', 'std reward']
    rows = []
    for i, label in enumerate(labels):
        rows.append([label, np.mean(data[i]), np.std(data[i])])

    if save_mode:
        with open("results/mc_model/" + folder_name + "/" "table_benchmarking", "w") as f:
            f.write(tabulate(rows, headers=headers))
    else:
        print("Results:\n")
        print(tabulate(rows, headers=headers))

    plt.figure(figsize=(12, 5))
    plt.boxplot(data, labels=labels)
    plt.title("Comparison of different strategies")
    plt.ylabel("reward")

    if save_mode:
        plt.savefig("results/mc_model/" + folder_name + "/" "box_plot_benchmarking")
    else:
        plt.show()


def evaluate_strategies_single_Q(file_name, args, n_test=1e2, c=1):
    """
    compares different strategies with boxplots and a table with mean and rewards

    Parameters
    ----------
    file_names : list
        a list with the paths for the Q-tables
    args : dict
        the parameters used for the environment
    n_test : int
        the number of episodes the strategies are evaluated for
    c : int
        the number of ticks the constant strategies uses

    Returns
    -------
    None
    """

    args_environment = args

    if args != None:
        # Get the constant rewards
        rewards_constant = evaluate_constant_strategy(args_environment, n=n_test, c=c)

        # Get the random rewards
        rewards_random = evaluate_random_strategy(args_environment, n=n_test)

    # Get the best Q-learning rewards
    rewards_Q_learning_best, _, _ = evaluate_Q_matrix(file_name, n=n_test)

    if args != None:
        data = [rewards_constant,
                rewards_random,
                rewards_Q_learning_best]

        labels = ["constant (d=" + str(c) + ")",
                  "random",
                  "Q_learning (best run)"]

    else:
        data = [rewards_Q_learning_best]

        labels = ["Q_learning (best run)"]

    headers = ['strategy', 'mean reward', 'std reward']
    rows = []
    for i, label in enumerate(labels):
        rows.append([label, np.mean(data[i]), np.std(data[i])])

    print("Results:\n")
    print(tabulate(rows, headers=headers))

    plt.figure(figsize=(12, 5))
    plt.boxplot(data, labels=labels)
    plt.title("Comparison of different strategies")
    plt.ylabel("reward")
    plt.show()


def compare_Q_learning_runs(file_names, n_test=1e2, folder_mode=False, folder_name=None, save_mode = False, dt=1, time_per_episode=1):
    """
    compares different Q-learning runs with boxplots and a table with mean and rewards

    Parameters
    ----------
    file_names : list
        a list with the paths for the Q-tables
    n_test : int
        the number of episodes the strategies are evaluated for
    folder_mode : bool
        whether or not things should be loaded/saved to files
    folder_name : str
        where files are saved
    save_mode : bool
        whether or not table and figures should be saved or displayed
    dt : int
        the size of the time step
    time_per_episode : int
        T, the length of the episode

    Returns
    -------
    None
    """

    data = []
    actions = []
    q_values = []

    for i, file_name in enumerate(file_names):
        print(".", end="")

        reward, action, q_value = evaluate_Q_matrix(file_name, n=n_test, folder_mode=folder_mode, folder_name=folder_name)
        data.append(reward)
        actions.append(action)
        q_values.append(q_value)

    labels = ["run " + str(i + 1) for i in range(len(file_names))]

    headers = ['run', 'mean reward', 'std reward', 'reward per action', 'reward per second', 'Q(0,0)', 'opt action']
    rows = []

    for i, label in enumerate(labels):
        rows.append([label, np.mean(data[i]), np.std(data[i]), np.mean(data[i]) / (time_per_episode / dt), 
                        np.mean(data[i]) / time_per_episode, q_values[i], actions[i]])

    if save_mode:
        with open("results/mc_model/" + folder_name + "/" "table_different_runs", "w") as f:
            f.write(tabulate(rows, headers=headers))
    else:
        print("Results:\n")
        print(tabulate(rows, headers=headers))
        print()

    plt.figure(figsize=(12, 5))
    plt.boxplot(data, labels=labels)
    plt.title("Comparison of different Q-learning runs")
    plt.ylabel("reward")

    if save_mode:
        plt.savefig("results/mc_model/" + folder_name + "/" "box_plot_different_runs")
    else:
        plt.show()

    return np.mean(data, axis=1)


def plot_rewards_multiple(file_names, folder_mode=False, folder_name=None, save_mode = False):
    """
    plots the reward and average q-value during training

    Parameters
    ----------
    matrix_path : str
        the file path for the Q-table to be evaluated
    n : int
        how many episodes that will be simulated
    folder_mode : bool
        whether or not things should be loaded/saved to files
    folder_name : str
        where files are saved
    save_mode : bool
        whether or not table and figures should be saved or displayed

    Returns
    -------
    None
    """

    reward_matrix = []
    Q_zero_matrix = []

    for file_name in file_names:
        _, _, _, rewards_average, Q_zero_average, x_values = load_Q(file_name, folder_mode=folder_mode, folder_name=folder_name)

        reward_matrix.append(rewards_average)
        Q_zero_matrix.append(Q_zero_average)

    reward_matrix = np.array(reward_matrix)
    Q_zero_matrix = np.array(Q_zero_matrix)

    reward_mean = np.mean(reward_matrix, axis=0)
    reward_std = np.std(reward_matrix, axis=0)

    Q_zero_mean = np.mean(Q_zero_matrix, axis=0)
    Q_zero_std = np.std(Q_zero_matrix, axis=0)

    reward_area = np.array([reward_std, -reward_std]) + reward_mean
    Q_zero_area = np.array([Q_zero_std, -Q_zero_std]) + Q_zero_mean

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 7))

    # Plot the rewards
    ax1.fill_between(x_values, reward_area[0, :], reward_area[1, :], alpha = 0.3, color="purple", label="±$\sigma$")
    ax1.plot(x_values, reward_mean, linewidth=0.2, color="purple", label="mean reward")
    ax1.set_xlabel('episode')
    ax1.set_ylabel('reward')
    ax1.set_title('average reward during training')

    # Plot the Q-values
    ax2.fill_between(x_values, Q_zero_area[0, :], Q_zero_area[1, :], alpha = 0.3, color="purple", label="±$\sigma$")
    ax2.plot(x_values, Q_zero_mean, linewidth=0.2, color="purple", label="mean Q[(0,0)]-value")
    ax2.set_xlabel('episode')
    ax2.set_ylabel('Q[(0,0)]')
    ax2.set_title('average Q[(0,0)] during training')

    ax1.legend()
    ax2.legend()

    if save_mode:
        plt.savefig("results/mc_model/" + folder_name + "/" "results_graph")
    else:
        plt.show()


def calculate_mean_Q(file_names, folder_mode=False, folder_name=None):
    """
    loads and returns Q-tables and their mean Q-table

    Parameters
    ----------
    file_names : list
        a list with strings of the save locations of Q-tables
    folder_mode : bool
        whether or not things should be loaded/saved to files
    folder_name : str
        where files are saved

    Returns
    -------
    Q_mean : dict
        the average Q-tables of all runs
    Q_tables : list
        a list with the loaded Q-tables
    """

    _, args, _, _, _, _ = load_Q(file_names[0], folder_mode=folder_mode, folder_name=folder_name)

    env = MonteCarloEnv(**args, debug=False)

    Q_mean = defaultdict(lambda: np.zeros(env._get_action_space_shape()))

    Q_tables = []

    for file_name in file_names:
        Q_tables.append(load_Q(file_name, folder_mode=folder_mode, folder_name=folder_name)[0])

    for state in list(Q_tables[0].keys()):
        Q_mean[state] = np.mean([Q_tables[i][state] if len(Q_tables[i][state].shape) == 3 else np.reshape(
            Q_tables[i][state], Q_tables[i][state].shape + (1,)) for i in range(len(Q_tables))], axis=0)

    return Q_mean, Q_tables


def calculate_std_Q(Q_mean, Q_tables):
    """
    calculates the standard deviation of every state-value for every possible state
    based on the given Q-tables. The mean Q-table is used to choose the optimal action.

    Parameters
    ----------
    Q_mean : dict
        the average Q-tables of all runs
    Q_tables : list
        a list with the loaded Q-tables

    Returns
    -------
    Q_std : dict
        the std of the Q-tables
    """

    Q_std = Q_mean

    for state in list(Q_mean.keys()):
        # Find the optimal action based on mean
        optimal_action = np.array(np.unravel_index(Q_mean[state].argmax(), Q_mean[state].shape))

        # Calculate the standard deviation of the q-value of that action
        Q_std[state] = np.std([Q_tables[i][state][(optimal_action[0], optimal_action[1])] for i in range(len(Q_tables))])
        if type(Q_std[state]) == np.ndarray:
            Q_std[state] = Q_std[state][0]

    return Q_std


def args_to_file_names(args, n_runs, n):
    """
    returns a list of file_names based on model parameters

    Parameters
    ----------
    args : dict
        a dict with model parameters
    n_runs : int
        the number of different runs performed
    n : int
        the number of episodes each runs is trained for

    Returns
    -------
    file_names : list
        a list with strings of file_names
    """

    suffixes = np.arange(n_runs) + 1

    file_names = []

    for suffix in suffixes:
        file_names.append(fetch_table_name(args, n, suffix))

    return file_names


def Q_learning_comparison(n_train=1e4, n_test=3e2, n_runs=3, file_names = None, args = None, 
                            Q_learning_args = None, folder_mode = False, folder_name = None, save_mode = False, skip_T = False):
    """
    runs tabular Q-learning several times (if not given file_names to load) 
    and compares them against eachother and other strategies

    Parameters
    ----------
    n_train : int
        the number of episodes the Q-learning is run for
    n_test : int
        the number of episodes the strategies are evaluated for
    n_runs : int
        how many times the Q-learning is performed
    file_names : list
        a list with strings of the save locations of Q-tables
    args : dict
        the parameters used for the environment
    Q_learning_args : dict
        the parameters used for the Q-learning
    folder_mode : bool
        whether or not things should be loaded/saved to files
    folder_name : str
        where files are saved
    skip_T : bool
        whether or not the final time step should be skipped in the heatmaps

    Returns
    -------
    None
    """

    if file_names == None:
        file_names = Q_learning_multiple(args, Q_learning_args, n_train, n_runs, folder_mode=folder_mode, folder_name=folder_name)
    
    env = MonteCarloEnv(**args)

    Q_mean, Q_tables = calculate_mean_Q(file_names, folder_mode=folder_mode, folder_name=folder_name)

    print()
    print("PLOTTING REWARDS...", end="")
    plot_rewards_multiple(file_names, folder_mode=folder_mode, folder_name=folder_name, save_mode=save_mode)
    print(" DONE")

    print()
    print("EVALUATING DIFFERENT Q-STRATEGIES", end="")
    mean_rewards = compare_Q_learning_runs(file_names, n_test, folder_mode=folder_mode, folder_name=folder_name, 
                                            save_mode=save_mode, dt=env.dt, time_per_episode=env.T)
    print(" DONE")

    print()
    print("EVALUATING DIFFERENT STRATEGIES", end="")
    evaluate_strategies_multiple_Q(file_names, args, mean_rewards, Q_mean, n_test, folder_mode=folder_mode, folder_name=folder_name, save_mode=save_mode)
    print(" DONE")

    print()
    print("SHOWING STRATEGIES...", end="")

    file_path = "results/mc_model/" + folder_name + "/" if save_mode else None

    show_Q(Q_mean, file_path = file_path)
    heatmap_Q(Q_mean, file_path = file_path, skip_T = skip_T)
    print(" DONE")

    print()
    print("SHOWING STD FOR Q MATRIX")
    Q_std = calculate_std_Q(Q_mean, Q_tables)
    heatmap_Q_std(Q_std, file_path = file_path)

    print()
    print("HEATMAP FOR ERRORS")
    heatmap_Q_n_errors(Q_mean.copy(), Q_tables.copy(), n_unique = True, file_path = file_path)
    heatmap_Q_n_errors(Q_mean.copy(), Q_tables.copy(), n_unique = False, file_path = file_path)


def single_run_evaluation(n_test, file_name=None, args=None):
    """
    runs tabular Q-learning once (if not given file_name to load) 
    and compares them against benchmark

    Parameters
    ----------
    n_test : int
        the number of episodes the strategies are evaluated for
    file_name : str
        a string of the save location of the Q-table
    args : dict
        the parameters used for the environment

    Returns
    -------
    None
    """

    if file_name == None:
        print("TRAINING THE AGENT")
        args = {"include_spread_levels": True, "num_levels": 10, "dt": 20, "T": 100,
                "num_time_buckets": 5, "kappa": 4, "pre_run_on_start": True}

        n = 1e4
        suffix = "Q-testing"

        env = MonteCarloEnv(**args, debug=False)

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


        save_Q(Q_tab, args, n, rewards_average, Q_zero_average, x_values, suffix)

        file_name = fetch_table_name(args, n, suffix)

    else:
        print("LOADING PREVIOUSLY TRAINED AGENT")

    print("\tloading file", file_name)
    Q_loaded = load_Q(file_name)[0]

    plot_rewards_multiple([file_name])

    if args != None:
        evaluate_strategies_single_Q(file_name, args, n_test=n_test)

    show_Q(Q_loaded)
    heatmap_Q(Q_loaded)


def get_args_from_txt(folder_name):
    """
    fetches arguments from a parameters.txt file

    Parameters
    ----------
    folder_name : str
        where the txt file is saved

    Returns
    -------
    args : dict
        the parameters used for the environment
    """

    f = open("results/mc_model/" + folder_name + "/parameters.txt")
    lines = f.readlines()

    args = {}

    for line in lines:
        if line == "\n":
            return args

        if line != "MODEL PARAMETERS\n":
            key, value = line.split(":")
            key = key.strip()
            value = value.strip()

            if value in ["True", "False"]:
                value == "True"
            else:
                value = float(value)
                if value == int(value):
                    value = int(value)

            args[key] = value

    return args


def evaluate_strategy_properties(Qs, Xs, Vs):
    """
    plots the inventory, cash and value process of a single run

    Parameters
    ----------
    Qs : np.array
        an array with inventory values
    Xs : np.array
        an array with cash values    
    Vs : np.array
        an array with current value of position 

    Returns
    -------
    None
    """

    Xs = Xs/100
    Vs = Vs/100

    fig, (q_axis, x_axis, v_axis) = plt.subplots(1, 3, figsize=(21, 7))

    q_axis.set_title("inventory process")
    x_axis.set_title("cash process")
    v_axis.set_title("value process")

    q_std = np.std(Qs, axis=0)
    q_mean = np.mean(Qs, axis=0)
    x_mean = np.mean(Xs, axis=0)
    x_std = np.std(Xs, axis=0)
    v_mean = np.mean(Vs, axis=0)
    v_std = np.std(Vs, axis=0)

    q_axis.plot(q_mean, color="purple")
    q_axis.fill_between(list(range(len(q_mean))), q_mean - q_std, q_mean + q_std, alpha=0.3, color="purple")
    q_axis.set_xlabel("t")
    q_axis.set_ylabel("Quantity")
    q_axis.get_yaxis().get_major_formatter().set_useOffset(False)

    x_axis.plot(x_mean, color="purple")
    x_axis.fill_between(list(range(len(x_mean))), x_mean - x_std, x_mean + x_std, alpha=0.3, color="purple")
    x_axis.set_xlabel("t")
    x_axis.set_ylabel("")
    x_axis.get_yaxis().get_major_formatter().set_useOffset(False)

    v_axis.plot(v_mean, color="purple")
    v_axis.fill_between(list(range(len(v_mean))), v_mean - v_std, v_mean + v_std, alpha=0.3, color="purple")
    v_axis.set_xlabel("t")
    v_axis.set_ylabel("")
    v_axis.get_yaxis().get_major_formatter().set_useOffset(False)


def evaluate_strategy_properties_multiple(all_Q, all_X, all_V):
    """
    plots the inventory, cash and value process for all runs simultaneously

    Parameters
    ----------
    Qs : np.array
        an array with inventory values for all runs
    Xs : np.array
        an array with cash values for all runs 
    Vs : np.array 
        an array with current value of position for all runs

    Returns
    -------
    None
    """

    fig, (q_axis, x_axis, v_axis) = plt.subplots(1, 3, figsize=(21, 7))

    q_axis.set_title("inventory process")
    x_axis.set_title("cash process")
    v_axis.set_title("value process")

    for i in range(len(all_X)):
        q_mean = np.mean(all_Q[i], axis=0)
        x_mean = np.mean(all_X[i], axis=0)
        v_mean = np.mean(all_V[i], axis=0)

        q_axis.plot(q_mean)
        x_axis.plot(x_mean)
        v_axis.plot(v_mean)

    q_axis.set_xlabel("t")
    q_axis.set_ylabel("Quantity")
    q_axis.get_yaxis().get_major_formatter().set_useOffset(False)
    q_axis.autoscale(enable=True, axis="y", tight=False)

    x_axis.set_xlabel("t")
    x_axis.set_ylabel("")
    x_axis.get_yaxis().get_major_formatter().set_useOffset(False)

    v_axis.set_xlabel("t")
    v_axis.set_ylabel("")
    v_axis.get_yaxis().get_major_formatter().set_useOffset(False)

    # legend
    fig.legend([f"run {i}" for i in range(1, len(all_Q)+1)], loc="lower right")

NUM_LEVELS = 10
INIT_ASK = 10001
INIT_SPREAD = 2
INIT_VOLUME = 1

if __name__ == "__main__":
    if False:
        # ===== TRAIN NEW AGENTS =====
        folder_mode = True              # If loading should be done from seperate folder
        folder_name = "dt10"   # The name of the folder

        save_mode = True                # If plots should be shown or saved

        # Arguments of the trained agents
        args = {"dt": 1, "T": 1000, "num_time_buckets": 5, "kappa": 5, "num_levels": 10,
                "pre_run_on_start": False, "pre_run_iterations": 5}

        # Remaining arguments
        n_test = 1e3
        n_runs = 1
        n_train = 1e2

        # Arguments of the Q-learning
        Q_learning_args = {
            "epsilon_start": 1, "epsilon_end": 0.05, "epsilon_cutoff": 0.5,
            "alpha_start": 0.5, "alpha_end": 0.0001,
            "beta_start": 1, "beta_end": 0.02, "beta_cutoff": 0.5,
            "exploring_starts": True
        }
        
        # Perform the comparison
        Q_learning_comparison(n_train=n_train, n_test=n_test, n_runs=n_runs,
            args=args, Q_learning_args=Q_learning_args,
            folder_mode=folder_mode, folder_name=folder_name, save_mode=save_mode)

    if False:
        # ===== LOADING OLD FILES =====

        folder_mode = True              # If loading should be done from seperate folder
        folder_name = "gcp_unbinned_v2"   # The name of the folder

        save_mode = True                # If plots should be shown or saved

        # Arguments of the trained agents
        args = get_args_from_txt(folder_name)
        
        # Remaining arguments
        n_test = 1e0
        n_runs = 8
        n_train = 1.6e6

        # Fetch the names of the tables to be loaded
        file_names = args_to_file_names(args, n_runs = n_runs, n = n_train)

        # Perform the comparison
        Q_learning_comparison(n_test=n_test, file_names=file_names, args=args,
                              folder_mode=folder_mode, folder_name=folder_name, save_mode=save_mode, skip_T=True)

    if False:

        folder_mode = True              # If loading should be done from separate folder
        folder_name = "gcp_MEGA_run"   # The name of the folder
        # folder_name = "gcp_ungrouped"
        args = get_args_from_txt(folder_name)

        save_mode = True                # If plots should be shown or saved

        n_test = 1e1
        n_runs = 8
        n_train = 4e4
        # n_train = 1600000

        # Fetch the names of the tables to be loaded
        file_names = args_to_file_names(args, n_runs = n_runs, n=n_train)

        Q_mean, Q_tables = calculate_mean_Q(file_names, folder_mode=folder_mode, folder_name=folder_name)

        return_X_Q_V = True

        rewards, _, _, Qs, Xs, Vs = evaluate_Q_matrix(_, n=n_test, args=args, Q_tab=Q_mean, return_X_Q_V=return_X_Q_V)

        evaluate_strategy_properties(Qs, Xs, Vs)

        print("Done")

    if False:
        folder_mode = True  # If loading should be done from separate folder
        folder_name = "gcp_unbinned_v2"  # The name of the folder
        # folder_name = "gcp_ungrouped"
        args = get_args_from_txt(folder_name)

        save_mode = True  # If plots should be shown or saved

        n_test = 1e3
        n_runs = 8
        # n_train = 4e4
        n_train = 1600000

        # Fetch the names of the tables to be loaded
        file_names = args_to_file_names(args, n_runs=n_runs, n=n_train)

        Q_mean, Q_tables = calculate_mean_Q(file_names, folder_mode=folder_mode, folder_name=folder_name)

        return_X_Q_V = True

        all_Q, all_X, all_V = list(), list(), list()

        for i in range(len(Q_tables)):
            print("Starting table", i+1)
            _, _, _, Qs, Xs, Vs = evaluate_Q_matrix(_, n=n_test, args=args, Q_tab=Q_mean, return_X_Q_V=return_X_Q_V)
            all_Q.append(Qs)
            all_X.append(Xs)
            all_V.append(Vs)

        print("succé")
        # evaluate_strategy_properties(Qs, Xs, Vs)
        evaluate_strategy_properties_multiple(all_Q, all_X, all_V)

        print("Done")



