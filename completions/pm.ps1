Register-ArgumentCompleter -CommandName pm, project-manager -ScriptBlock {
    param($wordToComplete, $commandAst, $cursorPosition)
    'scan','init','tui','workspace','check','doctor','version','git','open','history' |
        Where-Object { $_ -like "$wordToComplete*" } |
        ForEach-Object { [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_) }
}
