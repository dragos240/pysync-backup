![](imgs/logo.png)

# PySync-backup

## What is it?
PySync-backup is a incremental backup solution written in Python using the rsync utility. It is meant to be used in cron, but can be run individually if you like.

## How does it work?
PySync-backup creates `monthly`, `daily`, and `weekly` folders in your destination path and backs your source directory (`/` with exclusions by default) to each depending on when the last successful backup had been performed.

## Dependencies
PySync-backup has one dependency which is `pyyaml` which allows it to read the YAML configuration file. Install it with:

```
pip3 install --user pyyaml
```

(Note: You are welcome to remove the `--user` flag, but by doing so, you install to your system directoriess, which is not reccomended.)

## Configuration
PySync-backup can be configured by copying the `config.default.yml` file to one named `config.yml`. Please edit it to match your setup.

## Running
It's easy to run PySync-backup. Just run the `backup.py` script with:
```
./backup.py
```

Or alternatively:
```
python3 backup.py
```