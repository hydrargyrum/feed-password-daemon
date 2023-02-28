#!/usr/bin/env python3
# SPDX-License-Identifier: WTFPL

import argparse
import atexit
import datetime
import getpass
import os
import shlex
import signal
import sys
import time

import pexpect


def now():
	return datetime.datetime.now()


def on_exit():
	print(f"{now()}: exiting", file=sys.stderr)


def runchild(signum, frame):
	print(f"{now()}: will spawn {shlex.join(args.command)!r}", file=sys.stderr)

	child = pexpect.spawn(
		args.command[0], args.command[1:],
		encoding="utf8",
	)
	child.logfile_read = sys.stdout

	child.expect(args.reply_to_prompt)
	child.sendline(password)

	child.expect(pexpect.EOF)
	child.wait()
	print(f"{now()}: child process exited", file=sys.stderr)


def quit(*_):
	if args.pid_file:
		os.unlink(args.pid_file)
	exit(130)


parser = argparse.ArgumentParser()
parser.add_argument("--password-from-env", metavar="VARIABLE")
parser.add_argument("--password-from-file", metavar="FILE")
parser.add_argument("--password-from-stdin", action="store_true")
parser.add_argument("--reply-to-prompt", default="Password:", metavar="PROMPT")
parser.add_argument("--pid-file", metavar="FILE")
parser.add_argument(
	"--confirm-password", action="store_true",
	help="Prompt the password twice to make sure it's correct",
)
parser.add_argument(
	"--check-at-start", action="store_true",
	help="Run COMMAND immediately to check the password is correct",
)
parser.add_argument("command", nargs="+")
args = parser.parse_args()

if args.password_from_env:
	# unfortunately, pop() does not prevent the env variable from
	# being shown in `ps e`
	password = os.environ.pop(args.password_from_env)
elif args.password_from_file:
	with open(args.password_from_file) as fp:
		password = fp.readline().rstrip()
elif args.password_from_stdin:
	password = sys.stdin.readline().rstrip()
else:
	password = getpass.getpass(f"Password to feed to {shlex.join(args.command)!r}: ")
	if args.confirm_password:
		password2 = getpass.getpass("Confirm password: ")
		if password != password2:
			sys.exit("error: passwords are different, exiting")

signal.signal(signal.SIGUSR1, runchild)
signal.signal(signal.SIGINT, quit)

if args.pid_file:
	with open(args.pid_file, "w") as fp:
		print(os.getpid(), file=fp)

atexit.register(on_exit)

if args.check_at_start:
	runchild(None, None)

while True:
	# keep the program running so we receive SIGUSR1
	time.sleep(600)
