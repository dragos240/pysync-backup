#!/usr/bin/env python3
import argparse
from datetime import datetime, timedelta
from os import stat, path, mkdir
import subprocess as sp
from time import sleep

from pathlib import Path
import yaml


RSYNC_CMD = "rsync"


class Config:
    def __init__(self, config_path):
        with open(config_path, "r") as f:
            self.config = yaml.load(f.read(), Loader=yaml.FullLoader)
            # Normalize path for later use
            self.config["src_dir"] = path.normpath(self.config["src_dir"])
            self.config["dst_dir"] = path.normpath(self.config["dst_dir"])

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
            if not path.exists(path.join(period_path, self.last_file)):
                link_dst = path.join(self.dst_dir, self.monthly_dir)
        elif period == "weekly":
            period_path = path.join(self.dst_dir, self.weekly_dir)
            link_dst = path.join(self.dst_dir, self.daily_dir)
        if link_dst is not None:
            link_dst = path.join(link_dst, "")
        period_path = path.join(period_path, "")

        return period_path, link_dst

    def __getattr__(self, attr):
        if attr == "rsync_all":
            rsync_all = [RSYNC_CMD]
            rsync_all.extend(self.config["rsync_args"])
            for e in self.config["excluded"]:
                p = e
                if self.config["absolute_paths"]:
                    p = path.relpath(e, start=self.config["src_dir"])
                rsync_all.append("--exclude=" + p)
            return rsync_all
        if attr == "src_dir":
            return path.join(self.config["src_dir"], "")
        if attr in self.config:
            return self.config[attr]

        return None


class BackupController:
    def __init__(self, config, args):
        self.config = config
        self.dry_run = args.dry_run
        self.period = args.period

    def run(self):
        if self.period is not None:
            print("Test mode activated")

            self.backup(self.period)
            return

        try:
            for period in ["monthly", "daily", "weekly"]:
                period_path, link_dst = self.config.get_paths(period)

                # if path doesn't exist, create it
                if not path.exists(period_path):
                    mkdir(period_path)
                delta = self.check_last_modified(
                    self.config.get_last_path(period))
                if period == "monthly":
                    if delta is not None and delta < timedelta(days=28):
                        print("Monthly completed less than 28 days ago, "
                              + "skipping")
                        continue
                elif period == "weekly":
                    if delta is not None and delta < timedelta(days=6):
                        print("Weekly completed less than 6 days ago, "
                              + "skipping")
                        continue

                ret = self.backup(period)
                if ret is None:
                    return
        except KeyboardInterrupt:
            pass
        except PermissionError as e:
            print("Access to the path '{}' was denied".format(e.filename))

    def backup(self, period):
        rsync_all = self.config.rsync_all
        period_path, link_dst = self.config.get_paths(period)
        if link_dst is not None:
            rsync_all.append("--link-dest=" + link_dst)
        rsync_all.extend([self.config.src_dir, period_path])
        print("Runnning: " + " ".join(rsync_all))
        if self.dry_run:
            return 0

        """
        if backup is monthly, do a full backup

        if backup is daily, do a backup on last daily,
        or monthly if daily doesn't exist

        if backup is weekly, do a backup on last daily
        """
        print("Starting {} backup in 3 seconds".format(period))

        sleep(3)

        ret = None
        try:
            with open(self.config.log_path, "w") as f:
                ret = sp.run(rsync_all, stdout=f, stderr=f)
        except KeyboardInterrupt:
            print("Interrupt received, exiting...")

        self.update_last_file(period)

        return ret

    def update_last_file(self, period):
        last_path = self.config.get_last_path(period)
        Path(last_path).touch()

    def check_last_modified(self, last_path):
        try:
            st = stat(last_path)
        except FileNotFoundError:
            return None
        now = datetime.utcnow()
        then = datetime.fromtimestamp(st.st_mtime)
        delta = now - then

        return delta


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--period", "-p",
                        choices=['monthly', 'daily', 'weekly'],
                        help="Optional period test logic on. "
                        + "Options are monthly, daily, or weekly.",
                        default=None)
    parser.add_argument('--dry-run', '-d',
                        action='store_true',
                        help="Perform a dry run only printing the commands "
                        + "that would be executed.",
                        default=False)
    parser.add_argument('--config', '-c',
                        help="Specify an alternate config file path.",
                        default="./config.yml")

    args = parser.parse_args()

    try:
        config = Config(args.config)
    except FileNotFoundError:
        print("Please copy create a config.json first.")
        return
    except KeyError as e:
        print("Could not find key", e)
        return

    if not config.ignore_mountpoint_warning \
            and not path.ismount(config.dst_dir):
        print("Destination dir is not a mountpoint, closing")
        return

    controller = BackupController(config, args)
    controller.run()


if __name__ == "__main__":
    main()
