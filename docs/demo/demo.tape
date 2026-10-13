# Regenerate with: vhs docs/demo/demo.tape   (run from the repository root)
Output docs/demo/demo.gif

Set Shell "bash"
Set FontSize 15
Set Width 1300
Set Height 430
Set Padding 20
Set TypingSpeed 45ms
Set Theme "Catppuccin Mocha"

Hide
Type "export PATH=$PWD/.venv/bin:$PATH PS1='$ ' && cd docs/demo/app && clear"
Enter
Show

Type "cat supabase/migrations/001_notes.sql"
Sleep 300ms
Enter
Sleep 2s
Type "seamscan audit ."
Sleep 300ms
Enter
Sleep 5s
Type "echo $?"
Enter
Sleep 3s
