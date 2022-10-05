#!/bin/bash
# Common shell functions.

# echo error message in red, echo usage(), and exit
raise_with_usage() {
  echo_red "$*" >&2
  usage
  exit 1
}

raise() {
  echo_red "$*" >&2
  exit 1
}


# Easier-to-read way to define variable using a heredoc.
# Yoinked from https://stackoverflow.com/a/8088167
define() {
  read -r -d '' ${1} || true
}

# Prompt the user for a yes/no response.
# Exit codes:
#   0: user entered yes
#   2: STDIN is not a TTY
#   10: user entered no
#
prompt_yn() {
  local prompt ans skip
  if [ $# -ge 2 ]; then
    return
  fi

  if [ $# -ge 1 ]; then
    prompt="$1"
  else
    prompt="Continue?"
  fi

  if [ ! -t 0 ]; then
    echo >&2 "$prompt [y/n]"
    echo >&2 "prompt_yn: error: stdin is not a TTY!"
    return 2
  fi

  while true; do
    read -r -p "$prompt [y/n] " ans
    case "$ans" in
      Y|y|yes|YES|Yes)
        return
        ;;
      N|n|no|NO|No)
        return 10
        ;;
    esac
  done
}

echo_color() {
  local color code
  color="$1"
  shift

  case "$color" in
    red)  code=31 ;;
    green)  code=32 ;;
    yellow) code=33 ;;
    blue)   code=34 ;;
    purple) code=35 ;;
    cyan)   code=36 ;;
    *)
      echo >&2 "echo_color: unknown color $color"
      return 1
      ;;
  esac

  if [ -t 1 ]; then
    echo -ne "\\033[1;${code}m"
  fi

  echo -n "$*"

  if [ -t 1 ]; then
    echo -ne '\033[m'
  fi

  echo
}

echo_blue() {
  echo_color blue "$@"
}
echo_green() {
  echo_color green "$@"
}
echo_red() {
  echo_color red "$@"
}
echo_yellow() {
  echo_color yellow "$@"
}
echo_cyan() {
  echo_color cyan "$@"
}
echo_purple() {
  echo_color purple "$@"
}


# Print underscores as wide as the terminal screen
echo_color_horizontal_rule() {
  declare -i width # local integer
  width="${COLUMNS-80}"

  local color

  case $# in
    0) color=blue ;;
    1) color="$1" ;;
    *)
      echo >&2 "usage: echo_color_horizontal_rule [COLOR]"
      return 1
      ;;
  esac

  echo_color "$color" "$(printf "%0.s_" $(seq 1 "$width"))"
}

assert_file_not_exists() {
  if [ -e "$1" ]; then
    echo_red >&2 "error: \`$1' already exists!"
    return 1
  fi
}

assert_file_exists() {
  if [ ! -e "$1" ]; then
    echo_red >&2 "error: \`$1' does not exist!"
    return 1
  fi
}