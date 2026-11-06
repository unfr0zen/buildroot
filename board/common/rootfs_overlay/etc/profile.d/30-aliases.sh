[ -n "$PS1" ] || return

alias cd..='cd ..'
alias c='clear'
alias mkdir='mkdir -pv'
alias cp='cp -rv'
alias df='df -h'
alias du='du -ch'
alias top='htop'

alias ls='ls -lhF --color=auto'
alias lm='ls --color=auto'
alias ll='ls -lAhF --color=auto'

alias grep='grep --color=auto'
alias egrep='egrep --color=auto'
alias fgrep='fgrep --color=auto'

alias ping='ping -c 5'
alias fastping='ping -c 100 -i 0.2'
alias ports='netstat -tulanp'
alias wget='wget -c'

alias reboot='/sbin/reboot'
alias poweroff='/sbin/poweroff'
alias halt='/sbin/halt'

alias dmesg='dmesg --color=always'
alias ip='ip -color=auto'
