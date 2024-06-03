#!/usr/bin/env python3
# SPDX-License-Identifier: WTFPL

# /// script
# dependencies = ["pexpect"]
# ///

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
		timeout=args.timeout,
		encoding="utf8",
	)
	child.logfile_read = sys.stdout

	child.expect(args.reply_to_prompt)
	child.sendline(password)

	child.expect(pexpect.EOF)
	status = child.wait()
	print(f"{now()}: child process exited with code {status}", file=sys.stderr)


def quit(*_):
	if args.pid_file:
		os.unlink(args.pid_file)
	exit(130)


parser = argparse.ArgumentParser(
	description="""
	Prompt for a password and caches it, then idles.
	Runs COMMAND when SIGUSR1 is received, giving the password to COMMAND.

	For example can be used to prompt a password once, and periodically
	give the cached password to a short-lived program that requires it but
	won't cache it between runs.

	By default, the password is prompted on the TTY.
	""",
)

group = parser.add_mutually_exclusive_group()
group.add_argument(
	"--password-from-env", metavar="VARIABLE",
	help="Read initial password from environment VARIABLE instead of prompting it",
)
group.add_argument(
	"--password-from-file", metavar="FILE",
	help="Read initial password from FILE",
)
group.add_argument(
	"--password-from-stdin", action="store_true",
	help="Read initial password on standard input instead of from TTY",
)
group.add_argument(
	"--confirm-password", action="store_true",
	help="Prompt the password twice (on TTY) to make sure it's not mistyped",
)

parser.add_argument(
	"--reply-to-prompt", default="Password:", metavar="PROMPT",
	help="Give password to COMMAND when COMMAND outputs PROMPT",
)
parser.add_argument(
	"--pid-file", metavar="FILE",
	help="Write PID of feed-password-daemon to FILE",
)
parser.add_argument(
	"--check-at-start", action="store_true",
	help="Run COMMAND immediately to check the password is correct at start",
)
parser.add_argument(
	"--timeout", type=int, default=None,
	help="Wait at max TIMEOUT seconds for the prompt or the command to exit."
	+ " Default: wait indefinitely.",
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
