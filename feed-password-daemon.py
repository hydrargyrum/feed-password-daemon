#!/usr/bin/env python3
# SPDX-License-Identifier: WTFPL

# /// script
# dependencies = ["pexpect"]
# ///

import argparse
import atexit
import ctypes
import getpass
import logging
import os
import shlex
import signal
import sys
import time

import pexpect


__version__ = "0.10.0"


def on_exit():
	logging.info("exiting")


def runchild(signum, frame):
	logging.info("will spawn: %r", shlex.join(args.command))

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
	logging.info("child process exited with code %s", status)


def quit(*_):
	if args.pid_file:
		os.unlink(args.pid_file)
	exit(130)


def restart(*_):
	# we restart the daemon by replacing current process with an exec with
	# roughly the same args.
	new_args = [sys.executable, __file__]

	mappings = [
		(args.reply_to_prompt, "--reply-to-prompt"),
		(args.pid_file, "--pid-file"),
		(args.timeout, "--timeout"),
		(args.password_from_env, "--password-from-env"),
	]
	for value, key in mappings:
		if value:
			new_args.append(f"{key}={value}")
	if args.check_at_start:
		new_args.append("--check-at-start")
	if args.mlock:
		new_args.append("--mlock")

	# if password was in env variable, it can be read again.
	# but if it's from somewhere else, it probably can't be read again from
	# the same source, for example if it was prompted, but we don't want to
	# prompt it again!
	# so we'll write it on the stdin of the new process.
	if not args.password_from_env:
		new_args.append("--password-from-stdin")

	new_args.append("--")
	new_args.extend(args.command)

	if args.password_from_env:
		new_env = {
			**os.environ,
			# restore it as we pop'ed it earlier
			args.password_from_env: password,
		}
		logging.info("reloading by execing %r", new_args)
		os.execvpe(sys.executable, new_args, new_env)

	pipe_read, pipe_write = os.pipe2(0)

	pid = os.fork()
	if not pid:
		# the child process has the password too, it'll write it on
		# the its parent's stdin. its parent is expected to be a freshly
		# re-run process.
		os.close(pipe_read)
		encoded = f"{password}\n".encode()
		if os.write(pipe_write, encoded) != len(encoded):
			logging.error("could not write password for reloading process")
		os.close(pipe_write)
		os._exit(0)
	else:
		os.close(pipe_write)
		os.dup2(pipe_read, 0)
		logging.info("reloading by execing %r", new_args)
		os.execvp(sys.executable, new_args)


logging.basicConfig(
	level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
)

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
parser.add_argument(
	"--mlock", action="store_true",
	help="Keep feed-password-daemon (not the wrapped command) in RAM, so "
	+ "the password cannot get accidentaly stored into swap",
)
parser.add_argument("--version", action="version", version=__version__)
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

signal.signal(signal.SIGHUP, restart)
signal.signal(signal.SIGUSR1, runchild)
signal.signal(signal.SIGINT, quit)

if args.mlock:
	libc = ctypes.CDLL("libc.so.6")
	libc.mlockall(3)  # MCL_CURRENT | MCL_FUTURE

if args.pid_file:
	with open(args.pid_file, "w") as fp:
		print(os.getpid(), file=fp)

atexit.register(on_exit)

if args.check_at_start:
	runchild(None, None)

while True:
	# keep the program running so we receive SIGUSR1
	time.sleep(600)
