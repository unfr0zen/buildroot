[ -n "$BASH_VERSION" ] || return
[ -n "$PS1" ] || return
export STARSHIP_CONFIG=/etc/starship.toml
eval "$(starship init bash)"

# An empty command has no preexec timestamp and clears the displayed status.
nest_prompt_status() {
 if [[ -z ${STARSHIP_START_TIME-} ]]; then
  STARSHIP_CMD_STATUS=0
  STARSHIP_PIPE_STATUS=(0)
 fi
}
starship_precmd_user_func=nest_prompt_status
