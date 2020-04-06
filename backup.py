#!/usr/bin/env python3
import subprocess as sp
from os import stat, path, mkdir
from time import sleep
import json
from datetime import datetime, timedelta
from pathlib import Path

daily_dir = "daily"
weekly_dir = "weekly"
monthly_dir = "monthly"

excluded_dirs = [
    "/dev/*", "/proc/*", "/sys/*",
    "/tmp/*", "/run/*", "/mnt/*",
    "/media/*", "/lost+found"]

last_file = ".last"

rsync_cmd = "rsync"
rsync_args = [
    "-aAXv",
    "--delete",
    "--info=progress2",
    "--exclude={{{}}}".format(",".join(excluded_dirs))]


def check_last_modified(fulldst):
    lastpath = path.join(fulldst, last_file)
    try:
        st = stat(lastpath)
    except FileNotFoundError:
        Path(lastpath).touch()
        return timedelta()
    now = datetime.utcnow()
    then = datetime.fromtimestamp(st.st_mtime)
    delta = now - then

    return delta


def backup(src_dir, fulldst, linkdest=None):
    rsync_all = [rsync_cmd] \
        .extend(rsync_args)
    if linkdest is not None:
        rsync_all.append("--link-dest=" + linkdest)
    # if path doesn't exist, create it
    if not path.exists(fulldst):
        mkdir(fulldst)

    if monthly_dir in fulldst:
        # do full backup
        pass
    elif daily_dir in fulldst:
        # do backup based on last daily
        # or monthly if daily doesn't exist
        pass
    elif weekly_dir in fulldst:
        # do backup based on last daily
        pass
    ret = sp.run(rsync_all)

    return ret


def main():
    src_dir = None
    dst_dir = None
    try:
        with open("config.json", "r") as f:
            config = json.loads(f.read())
            src_dir = config["src_dir"]
            dst_dir = config["dst_dir"]
    except FileNotFoundError:
        print("Please copy create a config.json first.")
        return
    except KeyError as e:
        print("Could not find key", e)
        return

    try:
        for subdir in [daily_dir, weekly_dir, monthly_dir]:
            fulldst = path.join(dst_dir, subdir)
            delta = check_last_modified(fulldst)
            linkdest = None
            if subdir == monthly_dir:
                if delta < timedelta(days=28):
                    print("Monthly completed less than 28 days ago, skipping")
                    continue
                print("Starting monthly backup in 3 seconds")
            elif subdir == daily_dir:
                if delta == timedelta():
                    # this means daily was just created, backup monthly
                    linkdest = path.join(dst_dir, monthly_dir)
                elif delta < timedelta(hours=23):
                    print("Daily completed less than 23 hours ago, skipping")
                    continue
                print("Starting daily backup in 3 seconds")
            elif subdir == weekly_dir:
                linkdest = path.join(dst_dir, daily_dir)
                if delta < timedelta(days=6):
                    print("Weekly completed less than 6 days ago, skipping")
                    continue
                print("Starting weekly backup in 3 seconds")

            sleep(3)
            backup(src_dir, fulldst, linkdest)
    except KeyboardInterrupt:
        return


if __name__ == "__main__":
    main()
