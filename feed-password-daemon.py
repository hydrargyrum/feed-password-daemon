#!/usr/bin/env python3
# SPDX-License-Identifier: WTFPL

import argparse
import os
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


parser = argparse.ArgumentParser()
parser.add_argument("--password-from-env", metavar="VARIABLE")
parser.add_argument("--password-from-file", metavar="FILE")
parser.add_argument("--reply-to-prompt", default="Password:", metavar="PROMPT")
parser.add_argument("command", nargs="+")
args = parser.parse_args()

if args.password_from_env:
	# unfortunately, pop() does not prevent the env variable from
	# being shown in `ps e`
	password = os.environ.pop(args.password_from_env)
elif args.password_from_file:
	with open(args.password_from_file) as fp:
		password = fp.readline().rstrip()
else:
	password = sys.stdin.readline().rstrip()

signal.signal(signal.SIGUSR1, runchild)
# quit on SIGINT
signal.signal(signal.SIGINT, signal.SIG_DFL)

while True:
	# keep the program running so we receive SIGUSR1
	time.sleep(600)
