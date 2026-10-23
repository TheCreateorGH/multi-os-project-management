_pm_complete() {
    local commands="scan init tui workspace check doctor version git open history"
    if [[ ${COMP_CWORD} -eq 1 ]]; then
        COMPREPLY=($(compgen -W "$commands" -- "${COMP_WORDS[1]}"))
    elif [[ ${COMP_WORDS[1]} == "git" ]]; then
        COMPREPLY=($(compgen -W "init commit status remote install-hooks uninstall-hooks changelog release" -- "${COMP_WORDS[COMP_CWORD]}"))
    elif [[ ${COMP_WORDS[1]} == "version" ]]; then
        COMPREPLY=($(compgen -W "preview bump" -- "${COMP_WORDS[COMP_CWORD]}"))
    fi
}
complete -F _pm_complete pm project-manager
