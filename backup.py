#!/usr/bin/env python3
from datetime import datetime, timedelta
from os import stat, path, mkdir
import subprocess as sp
from time import sleep
import sys
from pathlib import Path

import yaml


RSYNC_CMD = "rsync"


class Config:
    def __init__(self):
        with open("config.default.yml", "r") as f:
            self.default_config = yaml.load(f.read(), Loader=yaml.FullLoader)
        with open("config.yml", "r") as f:
            self.config = yaml.load(f.read(), Loader=yaml.FullLoader)

    def get_last_path(self, period):
        last_path = path.join(self.get_paths(period)[0], self.last_file)

        return last_path

    def get_paths(self, period):
        period_path = self.dst_dir
        link_dst = None
        if period == "monthly":
            period_path = path.join(self.dst_dir, self.monthly_dir)
        elif period == "daily":
            period_path = path.join(self.dst_dir, self.daily_dir)
            if not path.exists(period_path):
                link_dst = path.join(self.dst_dir, self.monthly_dir)
        elif period == "weekly":
            period_path = path.join(self.dst_dir, self.weekly_dir)
            link_dst = path.join(self.dst_dir, self.daily_dir)

        return period_path, link_dst

    def __getattr__(self, attr):
        if attr == "rsync_all":
            rsync_all = [RSYNC_CMD]
            rsync_all.extend(self.config["rsync_args"])
            rsync_all.append("--exclude={{{}}}"
                             .format(",".join(self.config["excluded"])))
            return rsync_all
        if attr in self.config:
            return self.config[attr]
        if attr in self.default_config:
            return self.default_config[attr]

        return None


def update_last_file(last_path):
    Path(last_path).touch()


def check_last_modified(last_path):
    try:
        st = stat(last_path)
    except FileNotFoundError:
        return None
    now = datetime.utcnow()
    then = datetime.fromtimestamp(st.st_mtime)
    delta = now - then

    return delta


def backup(config, period=None):
    rsync_all = config.rsync_all
    period_path, link_dst = config.get_paths(period)
    if link_dst is not None:
        rsync_all.append("--link-dest=" + link_dst)
    rsync_all.extend([config.src_dir, period_path])
    print(rsync_all)

    """
    if backup is monthly, do a full backup

    if backup is daily, do a backup on last daily,
    or monthly if daily doesn't exist

    if backup is weekly, do a backup on last daily
    """

    ret = None
    try:
        with open(config.log_path, "w") as f:
            ret = sp.run(rsync_all, stdout=f, stderr=f)
    except KeyboardInterrupt:
        print("Interrupt received, exiting...")

    return ret


def main():
    try:
        config = Config()
    except FileNotFoundError:
        print("Please copy create a config.json first.")
        return
    except KeyError as e:
        print("Could not find key", e)
        return

    if len(sys.argv) > 1:
        print("Test mode activated")

        period = None
        mode = sys.argv[1]
        if mode == '-m':
            period = "monthly"
        elif mode == '-d':
            period = "daily"
        elif mode == '-w':
            period = "weekly"
        else:
            print("Not a valid flag.")
            return
        backup(config, period)
        return

    if not config.ignore_mountpoint_warning \
            and not path.ismount(config.dst_dir):
        print("Destination dir is not a mountpoint, closing")
        return

    try:
        for period in ["monthly", "daily", "weekly"]:
            period_path, link_dst = config.get_paths(period)

            # if path doesn't exist, create it
            if not path.exists(period_path):
                mkdir(period_path)
            delta = check_last_modified(config.get_last_path(period))
            if period == "monthly":
                if delta is not None and delta < timedelta(days=28):
                    print("Monthly completed less than 28 days ago, skipping")
                    continue
            elif period == "weekly":
                if delta is not None and delta < timedelta(days=6):
                    print("Weekly completed less than 6 days ago, skipping")
                    continue
            print("Starting {} backup in 3 seconds".format(period))

            sleep(3)
            ret = backup(config, period)
            if ret is None:
                return

            update_last_file(config.get_last_path(period))
    except KeyboardInterrupt:
        pass
    except PermissionError as e:
        print("Access to the path '{}' was denied".format(e.filename))


if __name__ == "__main__":
    main()
