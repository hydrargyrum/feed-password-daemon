#!/usr/bin/env python3
# SPDX-License-Identifier: WTFPL

import argparse
import getpass
import os
import shlex
import signal
import sys
import time

import pexpect


def runchild(signum, frame):
	child = pexpect.spawn(
		args.command[0], args.command[1:],
		encoding="utf8",
	)
	child.logfile_read = sys.stdout

	child.expect(args.reply_to_prompt)
	child.sendline(password)

	child.expect(pexpect.EOF)
	child.wait()


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

signal.signal(signal.SIGUSR1, runchild)
signal.signal(signal.SIGINT, quit)

if args.pid_file:
	with open(args.pid_file, "w") as fp:
		print(os.getpid(), file=fp)

while True:
	# keep the program running so we receive SIGUSR1
	time.sleep(600)
