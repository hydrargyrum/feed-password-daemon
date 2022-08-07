#!/usr/bin/env python3
# SPDX-License-Identifier: WTFPL

import argparse
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
parser.add_argument("--reply-to-prompt", default="Password:")
parser.add_argument("command", nargs="+")
args = parser.parse_args()

password = sys.stdin.readline().strip()

signal.signal(signal.SIGUSR1, runchild)
# quit on SIGINT
signal.signal(signal.SIGINT, signal.SIG_DFL)

while True:
	time.sleep(600)
