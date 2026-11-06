[ -n "$BASH_VERSION" ] || return
[ -n "$PS1" ] || return
export STARSHIP_CONFIG=/etc/starship.toml
eval "$(starship init bash)"
