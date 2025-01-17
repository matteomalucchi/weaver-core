import matplotlib.pyplot as plt
import os
import re
import pickle
from collections import defaultdict
import mplhep as hep
import yaml
import argparse
import time
import numpy as np
from scipy.ndimage import uniform_filter1d

# parse arguments
parser = argparse.ArgumentParser()
parser.add_argument("--show", action="store_true", default=False, help="show plots")
parser.add_argument("--save", action="store_true", default=False, help="save plots")
parser.add_argument(
    "--not-partial",
    action="store_true",
    default=False,
    help="ignore partial epochs in the plots",
)
parser.add_argument("--last-epoch", type=int, default=24, help="save plots")
parser.add_argument("--in-path", type=str, default="", help="input path")
parser.add_argument("--out-path", type=str, default="", help="output path")
parser.add_argument("--in-dict", type=str, default="total", help="input dictionary")
parser.add_argument(
    "--complete-dict", type=str, default="complete_dict", help="dictionary with names"
)
parser.add_argument("--name", type=str, default="", help="name of the configuration")
parser.add_argument(
    "--type", type=str, default="lite,full", help="name of the file with the dictionary"
)
parser.add_argument(
    "--num-partial", type=int, default=3, help="number of partial samplings per epoch"
)
parser.add_argument(
    "--history-config",
    type=str,
    default="history_config",
    help="name of the file with the dictionary",
)
parser.add_argument("--fig-size", type=str, default="13,13", help="size of the figure")
args = parser.parse_args()

fig_size=[int(k) for k in args.fig_size.split(",")]

# type of the network
if "," in args.type:
    NET_TYPES = [k for k in args.type.split(",")]
else:
    NET_TYPES = [args.type]

with open(f"{args.history_config}.yaml", "r") as stream:
    history_dict = yaml.safe_load(stream)["history_dict"]


def plot(out_dir, name, fig_handle, history):
    """Plot the history of the given figure handle
    and save it in the given output directory

    :param out_dir: output directory
    :param name: name of the plot
    :param fig_handle: figure handle
    """
    plt.xlabel("Epoch", fontsize=20, loc="right")
    plt.ylabel(history, fontsize=20, loc="top")
    hep.style.use("CMS")
    hep.cms.label("Preliminary")
    hep.cms.label(year="UL18")
    # plt.suptitle(name, horizontalalignment='center', verticalalignment='top', fontsize=25)

    plt.legend(
        fontsize="15",
        # loc="lower right",
        # labelcolor='linecolor'
    )
    plt.grid()
    plt.savefig(f"{out_dir}/history_{name}.png", bbox_inches="tight")
    if args.save:
        with open(f"{out_dir}/history_{name}.pickle", "wb") as f:
            pickle.dump(fig_handle, f)
    if args.show:
        plt.show()
    plt.close()


def load_dict(complete_dict, in_dict):
    """Load the dictionary with the information to plot
    :param    complete_dict : string with the name of the file containing the paths to the models
    :param    in_dict : string with the name of the file containing the names of the models to load
    :return   info_dict : dictionary with the models to load
    """
    with open(complete_dict, "r") as stream:
        loaded_dict = yaml.safe_load(stream)
    with open(in_dict, "r") as stream:
        in_names = yaml.safe_load(stream)["networks"]
    info_dict = defaultdict(list)
    for k, v in loaded_dict.items():
        if v[0] not in in_names:
            continue
        # dictionary with the path, the name of the model, the color and the linestyle
        info_dict[k].append(defaultdict(list))
        info_dict[k].append(v[0])
        info_dict[k].append(v[1])
        info_dict[k].append(v[2])
    return info_dict


def draw_plot(value, num_tot, info, save):
    if len(value[:num_tot]) == num_tot:
        x_part = np.linspace(
            -(args.num_partial - 1) / args.num_partial, 0, args.num_partial
        )
        x = np.concatenate([x_part + i for i in range(1, args.last_epoch + 2)])
        # y=value[:num_tot]
        y = uniform_filter1d(value[:num_tot], size=args.num_partial)
    else:
        x = np.linspace(
            0, len(value[: args.last_epoch]), len(value[: args.last_epoch + 1])
        )
        y = value[: args.last_epoch + 1]
    plt.plot(x, y, color=info[2], linestyle=info[3], label=f"{info[1]}")
    save = True

    return save


if __name__ == "__main__":
    tot_dict = {}
    # create output directory
    date_time = time.strftime("%Y%m%d-%H%M%S")
    main_out_dir = os.path.join(
        f"{args.out_path}history_plot",
        f"{date_time}_{args.name}_{args.in_dict}_{args.type}_history",
    )
    os.makedirs(main_out_dir, exist_ok=True)
    print(main_out_dir)

    for net_type in NET_TYPES:
        infile_dict = load_dict(
            f"config/{args.complete_dict}.yaml",
            f"config/{args.in_dict}_{net_type}.yaml",
        )
        out_dir = os.path.join(
            main_out_dir, f"{args.name}_{args.in_dict}_{net_type}_history"
        )
        os.makedirs(out_dir, exist_ok=True)

        # load history for each input
        for input_name, info in infile_dict.items():
            # get all log files in the input directory and sort them in alphabetical order
            if isinstance(input_name, str):
                dir_name = os.path.join(args.in_path, input_name)
                infiles = [
                    os.path.join(dir_name, filename)
                    for filename in os.listdir(dir_name)
                    if ".log" in filename
                ]
                infiles.sort()  # key=lambda s: int(re.findall(r'\d+', s)[-1]))
            # get specific log files and sort them in alphabetical order
            elif isinstance(input_name, list):
                infiles = [
                    os.path.join(args.in_path + "input", "logs", f"{k}.log")
                    for k in input_name
                ]
                infiles.sort()  # key=lambda s: int(re.findall(r'\d+', s)[-1]))
            # print(input_name, infiles)
            # read the log files and extract the information
            for infile in infiles:
                with open(infile) as f:
                    f = f.readlines()
                # find the line with the information and save it in the dictionary
                for line in f:
                    for name, value in history_dict.items():
                        if value[0] in line:
                            if args.not_partial and "Partial" in line:
                                continue
                            val = float(line.split(value[0], 1)[1].split(value[1])[0])

                            # if "training" in name and len(info[0][name]) > 0:
                            #     if "Jet" in name and "accuracy" in name and (val - info[0][name][-1]) > 0.05 * info[0][name][-1]:
                            #         val = info[0][name][-1]+(val - info[0][name][-1])*0.01
                            #     elif "Jet" in name and "loss" in name and (info[0][name][-1]-val) > 0.1 * info[0][name][-1]:
                            #         val = info[0][name][-1]+(val - info[0][name][-1])*0.01
                            if len(info[0][name]) > 0:
                                if (val - info[0][name][-1]) > info[0][name][-1]:
                                    if "clas" in input_name and "Jet" in name:
                                        print(
                                            input_name,
                                            "name",
                                            name,
                                            "old_val",
                                            info[0][name][-1],
                                            "val",
                                            val,
                                        )
                                    val = (
                                        info[0][name][-1]
                                        + (val - info[0][name][-1])
                                        * info[0][name][-1]
                                        / val   /10
                                    )
                                elif (info[0][name][-1] - val) > val:
                                    if "clas" in input_name and "Jet" in name:
                                        print(
                                            input_name,
                                            "name",
                                            name,
                                            "old_val",
                                            info[0][name][-1],
                                            "val",
                                            val,
                                        )
                                    val = (
                                        info[0][name][-1]
                                        - (info[0][name][-1] - val)
                                        * val
                                        / info[0][name][-1]   /10
                                    )
                            # if val > 100:
                            #     val = -1

                            # print("name", name , "old_loss", old_loss, "val", val)
                            info[0][name].append(val)
            for name, value in history_dict.items():
                if "training" in name and len(info[0][name]) > 0:
                    for i in [42, 43, 44]:
                        # print("name", name, info[0][name], len(info[0][name]))
                        info[0][name][i] = (info[0][name][41] + info[0][name][45]) / 2

        tot_dict[net_type] = infile_dict

        # plot the history
        num_tot = (args.last_epoch + 1) * args.num_partial
        for history, _ in history_dict.items():
            fig_handle = plt.figure(figsize=(fig_size[0], fig_size[1]))
            save = False
            for _, info in infile_dict.items():
                for name, value in info[0].items():
                    if name == history and any(val != 0 for val in value):
                        save = draw_plot(value, num_tot, info, save)
            # call function plot only if figure is not empty
            if save:
                plot(
                    out_dir,
                    f'{history.replace(" ", "_")}_{args.in_dict}_{net_type}',
                    fig_handle,
                    history,
                )
            else:
                plt.close()

    if len(NET_TYPES) > 1:
        infile_dict = load_dict(
            f"config/{args.complete_dict}.yaml",
            f"config/{args.in_dict}_{NET_TYPES[0]}.yaml",
        )
        out_dir = os.path.join(
            main_out_dir, f"{args.name}_{args.in_dict}_{args.type}_history"
        )
        os.makedirs(out_dir, exist_ok=True)

        # plot the history
        num_tot = (args.last_epoch + 1) * args.num_partial
        for history, _ in history_dict.items():
            fig_handle = plt.figure(figsize=(fig_size[0], fig_size[1]))
            save = False
            for net_type in NET_TYPES:
                for _, info in tot_dict[net_type].items():
                    for name, value in info[0].items():
                        if name == history and any(val != 0 for val in value):
                            save = draw_plot(value, num_tot, info, save)
            # call function plot only if figure is not empty
            if save:
                plot(
                    out_dir,
                    f'{history.replace(" ", "_")}_{args.in_dict}_{args.type}',
                    fig_handle,
                    history,
                )
            else:
                plt.close()


"""
import pickle
figx = pickle.load(open('FigureObject.fig.pickle', 'rb'))

figx.show()
"""
