#!/usr/bin/env python3
"""
signals.py
"""
from __future__ import print_function

import signal
import sys
import time

import harness
from harness import register


#
# Test Cases
#
# TODO:
# - Fold code from demo/
#   - sigwinch-bug.sh -- invokes $OSH with different snippets, then manual window resize
#   - signal-during-read.sh -- bash_read and osh_read with manual kill -HUP $PID
#     trap handler HUP
#   - bug-858-trap.sh -- wait and kill -USR1 $PID
#     trap handler USR1
#     trap handler USR2
# - Fill out this TEST MATRIX.
#
# A. Which shell?  osh, bash, dash, etc.
#
# B. What mode is it in?
#
#    1. Interactive (stdin is a terminal)
#    2. Non-interactive
#
# C. What is the main thread of the shell doing?
#
#    1. waiting for external process: sleep 1
#    2. wait builtin:                 sleep 5 & wait
#       variants: wait -n: this matters when testing exit code
#    3. read builtin                  read
#       variants: FIVE kinds, read -d, read -n, etc.
#    4. computation, e.g. fibonacci with $(( a + b ))
#
# if interactive:
#    5. keyboard input from terminal with select()
#
#    Another way to categorize the main loop:
#    1. running script code
#    2. running trap code
#    3. running TAB completion plugin code
#
# D. What is it interrupted by?
#
#    1. SIGINT
#    2. SIGTSTP
#    3. SIGWINCH
#    4. SIGUSR1 -- doesn't this quit?
#
# if interactive:
#    1. SIGINT  Ctrl-C from terminal (relies on signal distribution to child?)
#    2. SIGTSTP Ctrl-Z from terminal
#
# E. What is the signal state?
#
#    1. no trap handlers installed
#    2. trap 'echo X' SIGWINCH
#    3. trap 'echo X' SIGINT ?


@register()
def sighup_trapped_wait(sh):
  'trapped SIGHUP during wait builtin'

  sh.sendline("trap 'echo HUP' HUP")
  sh.sendline('sleep 1 &')
  sh.sendline('wait')

  time.sleep(0.1)

  sh.kill(signal.SIGHUP)

  sh.expect(r'.*\$')  # expect prompt

  sh.sendline('echo status=$?')
  sh.expect('status=129')


@register()
def sigint_trapped_wait(sh):
  'trapped SIGINT during wait builtin'

  # This is different than Ctrl-C during wait builtin, because it's trapped!

  sh.sendline("trap 'echo INT' INT")
  sh.sendline('sleep 1 &')
  sh.sendline('wait')

  time.sleep(0.1)

  # simulate window size change
  sh.kill(signal.SIGINT)

  sh.expect(r'.*\$')  # expect prompt

  sh.sendline('echo status=$?')
  sh.expect('status=130')


@register()
def sigwinch_trapped_wait(sh):
  'trapped SIGWINCH during wait builtin'

  sh.sendline("trap 'echo WINCH' WINCH")
  sh.sendline('sleep 1 &')
  sh.sendline('wait')

  time.sleep(0.1)

  # simulate window size change
  sh.kill(signal.SIGWINCH)

  sh.expect(r'.*\$')  # expect prompt

  sh.sendline('echo status=$?')
  sh.expect('status=156')


@register()
def sigwinch_untrapped_wait(sh):
  'untrapped SIGWINCH during wait builtin (issue 1067)'

  sh.sendline('sleep 1 &')
  sh.sendline('wait')

  time.sleep(0.1)

  # simulate window size change
  sh.kill(signal.SIGWINCH)

  sh.expect(r'.*\$')  # expect prompt

  sh.sendline('echo status=$?')
  sh.expect('status=0')


@register()
def sigwinch_untrapped_wait_n(sh):
  'untrapped SIGWINCH during wait -n'

  sh.sendline('sleep 1 &')
  sh.sendline('wait -n')

  time.sleep(0.1)

  # simulate window size change
  sh.kill(signal.SIGWINCH)

  sh.expect(r'.*\$')  # expect prompt

  sh.sendline('echo status=$?')
  sh.expect('status=0')


@register()
def sigwinch_untrapped_external(sh):
  'untrapped SIGWINCH during external command'

  sh.sendline('sleep 0.5')  # slower than timeout

  time.sleep(0.1)

  # simulate window size change
  sh.kill(signal.SIGWINCH)

  sh.expect(r'.*\$')  # expect prompt

  sh.sendline('echo status=$?')
  sh.expect('status=0')


@register()
def sigwinch_untrapped_pipeline(sh):
  'untrapped SIGWINCH during pipeline'

  sh.sendline('sleep 0.5 | echo x')  # slower than timeout

  time.sleep(0.1)

  # simulate window size change
  sh.kill(signal.SIGWINCH)

  sh.expect(r'.*\$')  # expect prompt

  sh.sendline('echo pipestatus=${PIPESTATUS[@]}')
  sh.expect('pipestatus=0 0')


@register()
def t1(sh):
  'Ctrl-C during external command'

  sh.sendline('sleep 5')

  time.sleep(0.1)
  sh.sendintr()  # SIGINT

  sh.expect(r'.*\$')  # expect prompt

  sh.sendline('echo status=$?')
  sh.expect('status=130')


@register()
def t4(sh):
  'Ctrl-C during pipeline'
  sh.sendline('sleep 5 | cat')

  time.sleep(0.1)
  sh.sendintr()  # SIGINT

  sh.expect(r'.*\$')  # expect prompt

  sh.sendline('echo status=$?')
  sh.expect('status=130')


@register()
def t2(sh):
  'Ctrl-C during read builtin'

  sh.sendline('read myvar')

  time.sleep(0.1)
  sh.sendintr()  # SIGINT

  sh.expect(r'.*\$')  # expect prompt

  sh.sendline('echo status=$?')
  sh.expect('status=130')


@register()
def c_wait(sh):
  'Ctrl-C (untrapped) during wait builtin'

  sh.sendline('sleep 5 &')
  sh.sendline('wait')

  time.sleep(0.1)

  # TODO: actually send Ctrl-C through the terminal, not SIGINT?
  sh.sendintr()  # SIGINT

  sh.expect(r'.*\$')  # expect prompt

  sh.sendline('echo status=$?')
  sh.expect('status=130')


@register()
def c_wait_n(sh):
  'Ctrl-C (untrapped) during wait -n builtin'

  sh.sendline('sleep 5 &')
  sh.sendline('wait -n')

  time.sleep(0.1)

  # TODO: actually send Ctrl-C through the terminal, not SIGINT?
  sh.sendintr()  # SIGINT

  sh.expect(r'.*\$')  # expect prompt

  sh.sendline('echo status=$?')
  sh.expect('status=130')


@register()
def t5(sh):
  'Ctrl-C during Command Sub (issue 467)'
  sh.sendline('`sleep 5`')

  time.sleep(0.1)
  sh.sendintr()  # SIGINT

  sh.expect(r'.*\$')  # expect prompt

  sh.sendline('echo status=$?')
  # TODO: This should be status 130 like bash
  sh.expect('status=130')


@register(skip_shells=['bash'])
def t6(sh):
  'fg twice should not result in fatal error (issue 1004)'
  sh.expect(r'.*\$ ')
  sh.sendline("cat")
  stop_process__hack("cat")
  sh.expect("\r\n\\[PID \\d+\\] Stopped")
  sh.expect(r".*\$")
  sh.sendline("fg")
  sh.expect(r"Continue PID \d+")

  #sh.sendcontrol("c")
  sh.sendintr()  # SIGINT

  sh.expect(r".*\$")
  sh.sendline("fg")
  sh.expect("No job to put in the foreground")


@register(skip_shells=['bash'])
def t7(sh):
  'Test resuming a killed process'
  sh.expect(r'.*\$ ')
  sh.sendline("cat")
  stop_process__hack("cat")
  sh.expect("\r\n\\[PID \\d+\\] Stopped")
  sh.expect(r".*\$")
  sh.sendline("fg")
  sh.expect(r"Continue PID \d+")
  send_signal("cat", signal.SIGINT)
  sh.expect(r".*\$")
  sh.sendline("fg")
  sh.expect("No job to put in the foreground")


@register(skip_shells=['bash'])
def t8(sh):
  'Call fg after process exits (issue 721)'

  sh.expect(r".*\$")
  sh.sendline("cat")

  #osh.sendcontrol("c")
  sh.sendintr()  # SIGINT

  sh.expect(r".*\$")
  sh.sendline("fg")
  sh.expect("No job to put in the foreground")
  sh.expect(r".*\$")
  sh.sendline("fg")
  sh.expect("No job to put in the foreground")
  sh.expect(r".*\$")


@register()
def t9(sh):
  'syntax error makes status=2'

  sh.sendline('syntax ) error')

  #time.sleep(0.1)

  sh.expect(r'.*\$')  # expect prompt

  sh.sendline('echo status=$?')
  sh.expect('status=2')  # osh, bash, dash

  # mksh gives status=1, and zsh doesn't give anything?


if __name__ == '__main__':
  try:
    harness.main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)